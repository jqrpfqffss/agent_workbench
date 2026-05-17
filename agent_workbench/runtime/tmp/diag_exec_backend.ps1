param(
  [string]$Port,
  [int]$Baudrate,
  [int]$DataBits,
  [string]$ParityName,
  [string]$StopBitsName,
  [string]$FormatCode,
  [string]$LogPath,
  [string]$RequestFile,
  [string]$ResultFile,
  [string]$EncodingName,
  [int]$ReadTimeoutMs,
  [int]$StartupDrainMs,
  [int]$ResponseTimeoutMs,
  [int]$ResponseIdleTimeoutMs
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$requests = Get-Content -Raw -Path $RequestFile -Encoding UTF8 | ConvertFrom-Json
$serial = New-Object System.IO.Ports.SerialPort $Port, $Baudrate, ([System.IO.Ports.Parity]::$ParityName), $DataBits, ([System.IO.Ports.StopBits]::$StopBitsName)
$serial.ReadTimeout = $ReadTimeoutMs
$serial.WriteTimeout = [Math]::Max($ReadTimeoutMs, 100)
$script:exitCode = 0
$script:errorText = ""
$script:exchanges = New-Object System.Collections.Generic.List[object]

function Get-Timestamp {
  return [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffzzz")
}

function Append-Utf8([string]$path, [string]$line) {
  $writer = New-Object System.IO.StreamWriter($path, $true, (New-Object System.Text.UTF8Encoding($false)))
  try {
    $writer.WriteLine($line)
  } finally {
    $writer.Dispose()
  }
}

function Write-Log([string]$line) {
  Append-Utf8 $LogPath $line
}

function Get-Decoding {
  try {
    return [System.Text.Encoding]::GetEncoding($EncodingName)
  } catch {
    return [System.Text.Encoding]::UTF8
  }
}

function Escape-Preview([string]$text) {
  $builder = New-Object System.Text.StringBuilder
  foreach ($char in $text.ToCharArray()) {
    $code = [int][char]$char
    if ($char -eq "`r") {
      [void]$builder.Append('\r')
    } elseif ($char -eq "`n") {
      [void]$builder.Append('\n')
    } elseif ($char -eq "`t") {
      [void]$builder.Append('\t')
    } elseif (-not [char]::IsControl($char)) {
      [void]$builder.Append($char)
    } elseif ($code -le 255) {
      [void]$builder.Append(('\x{0:X2}' -f $code))
    } else {
      [void]$builder.Append(('\u{0:X4}' -f $code))
    }
  }
  return $builder.ToString()
}

function Bytes-ToHex([byte[]]$bytes) {
  if (-not $bytes -or $bytes.Length -eq 0) {
    return ""
  }
  $parts = foreach ($byte in $bytes) { '{0:X2}' -f [int]$byte }
  return [string]::Join(' ', $parts)
}

function Bytes-ToPreview([byte[]]$bytes) {
  if (-not $bytes -or $bytes.Length -eq 0) {
    return ""
  }
  return Escape-Preview((Get-Decoding).GetString($bytes))
}

function Read-AvailableBytes {
  $buffer = New-Object System.Collections.Generic.List[byte]
  while ($serial.BytesToRead -gt 0) {
    $chunk = New-Object byte[] $serial.BytesToRead
    $read = $serial.Read($chunk, 0, $chunk.Length)
    for ($index = 0; $index -lt $read; $index++) {
      $buffer.Add([byte]$chunk[$index])
    }
  }
  return [byte[]]$buffer.ToArray()
}

function Read-ChunkSafe {
  try {
    if ($serial.BytesToRead -gt 0) {
      return Read-AvailableBytes
    }
    $firstByte = $serial.ReadByte()
    if ($firstByte -lt 0) {
      return [byte[]]@()
    }
    $buffer = New-Object System.Collections.Generic.List[byte]
    $buffer.Add([byte]$firstByte)
    foreach ($extraByte in (Read-AvailableBytes)) {
      $buffer.Add([byte]$extraByte)
    }
    return [byte[]]$buffer.ToArray()
  } catch [System.TimeoutException] {
    return [byte[]]@()
  }
}

function Drain-Startup([int]$durationMs) {
  if ($durationMs -le 0) {
    return [byte[]]@()
  }
  $buffer = New-Object System.Collections.Generic.List[byte]
  $deadline = [DateTime]::UtcNow.AddMilliseconds($durationMs)
  while ([DateTime]::UtcNow -lt $deadline) {
    $chunk = Read-ChunkSafe
    foreach ($byte in $chunk) {
      $buffer.Add([byte]$byte)
    }
  }
  return [byte[]]$buffer.ToArray()
}

function Read-Response([int]$firstByteTimeoutMs, [int]$idleTimeoutMs) {
  $buffer = New-Object System.Collections.Generic.List[byte]
  $firstDeadline = [DateTime]::UtcNow.AddMilliseconds($firstByteTimeoutMs)
  while ([DateTime]::UtcNow -lt $firstDeadline) {
    $chunk = Read-ChunkSafe
    if ($chunk.Length -gt 0) {
      foreach ($byte in $chunk) {
        $buffer.Add([byte]$byte)
      }
      break
    }
  }
  if ($buffer.Count -eq 0) {
    return @{ bytes = [byte[]]@(); timed_out = $true }
  }

  $idleDeadline = [DateTime]::UtcNow.AddMilliseconds($idleTimeoutMs)
  while ([DateTime]::UtcNow -lt $idleDeadline) {
    $chunk = Read-ChunkSafe
    if ($chunk.Length -gt 0) {
      foreach ($byte in $chunk) {
        $buffer.Add([byte]$byte)
      }
      $idleDeadline = [DateTime]::UtcNow.AddMilliseconds($idleTimeoutMs)
    }
  }
  return @{ bytes = [byte[]]$buffer.ToArray(); timed_out = $false }
}

function To-ByteArray($data) {
  $buffer = New-Object byte[] $data.Count
  for ($index = 0; $index -lt $data.Count; $index++) {
    $buffer[$index] = [byte]$data[$index]
  }
  return $buffer
}

try {
  Write-Log ("[{0}] [diag] start port={1} baud={2} format={3} backend=powershell" -f (Get-Timestamp), $Port, $Baudrate, $FormatCode)
  $serial.Open()
  $serial.DiscardInBuffer()
  $serial.DiscardOutBuffer()

  $drained = Drain-Startup $StartupDrainMs
  if ($drained.Length -gt 0) {
    Write-Log ("[{0}] [diag] startup-drain hex={1} preview={2}" -f (Get-Timestamp), (Bytes-ToHex $drained), (Bytes-ToPreview $drained))
  }

  foreach ($request in $requests) {
    $requestBytes = To-ByteArray $request.data
    Write-Log ("[{0}] > index={1} hex={2} preview={3}" -f (Get-Timestamp), $request.index, $request.hex_text, $request.preview)
    $serial.Write($requestBytes, 0, $requestBytes.Length)

    $response = Read-Response $ResponseTimeoutMs $ResponseIdleTimeoutMs
    $responseBytes = [byte[]]$response.bytes
    $timedOut = [bool]$response.timed_out
    $responseHex = Bytes-ToHex $responseBytes
    $responsePreview = Bytes-ToPreview $responseBytes
    $exchangeStatus = if ($timedOut) { "timeout" } else { "ok" }
    if ($timedOut) {
      Write-Log ("[{0}] < index={1} [timeout]" -f (Get-Timestamp), $request.index)
      $script:exitCode = 41
    } else {
      Write-Log ("[{0}] < index={1} hex={2} preview={3}" -f (Get-Timestamp), $request.index, $responseHex, $responsePreview)
    }

    $script:exchanges.Add([ordered]@{
      index = [int]$request.index
      request_hex = [string]$request.hex_text
      request_preview = [string]$request.preview
      response_hex = [string]$responseHex
      response_preview = [string]$responsePreview
      response_size = [int]$responseBytes.Length
      timed_out = [bool]$timedOut
      status = [string]$exchangeStatus
    })

    if ($timedOut) {
      break
    }
  }
} catch {
  $script:errorText = $_.Exception.Message
  if ($script:exitCode -eq 0) {
    $script:exitCode = 42
  }
  Write-Log ("[{0}] [diag] backend-error {1}" -f (Get-Timestamp), $script:errorText)
} finally {
  if ($serial.IsOpen) {
    $serial.Close()
  }
  Write-Log ("[{0}] [diag] stop" -f (Get-Timestamp))
}

$requestHexes = @()
foreach ($request in $requests) {
  $requestHexes += [string]$request.hex_text
}
$finalStatus = if ($script:exitCode -eq 0) { "ok" } else { "error" }
$exchangeArray = @($script:exchanges.ToArray())
$payload = [ordered]@{}
$payload["generated_at"] = Get-Timestamp
$payload["status"] = [string]$finalStatus
$payload["exit_code"] = [int]$script:exitCode
$payload["backend"] = "powershell"
$payload["port"] = [string]$Port
$payload["baudrate"] = [int]$Baudrate
$payload["encoding"] = [string]$EncodingName
$payload["log_path"] = [string]$LogPath
$payload["result_path"] = [string]$ResultFile
$payload["request_count"] = [int]$requests.Count
$payload["exchange_count"] = [int]$script:exchanges.Count
$payload["requests"] = @($requestHexes)
$payload["exchanges"] = @($exchangeArray)
$payload["error"] = [string]$script:errorText
$payload | ConvertTo-Json -Depth 6 | Set-Content -Path $ResultFile -Encoding UTF8
