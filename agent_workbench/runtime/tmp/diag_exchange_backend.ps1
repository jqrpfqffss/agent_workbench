param(
  [string]$Port,
  [int]$Baudrate,
  [string]$RequestFile,
  [string]$ResultFile,
  [string]$LogPath,
  [int]$ReadTimeoutMs,
  [int]$ResponseTimeoutMs,
  [int]$SilenceTimeoutMs,
  [int]$ExpectedLength
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$raw = Get-Content -Raw -Path $RequestFile -Encoding UTF8 | ConvertFrom-Json
$request = New-Object byte[] $raw.Count
for ($i = 0; $i -lt $raw.Count; $i++) {
  $request[$i] = [byte]$raw[$i]
}
$serial = New-Object System.IO.Ports.SerialPort $Port, $Baudrate, ([System.IO.Ports.Parity]::None), 8, ([System.IO.Ports.StopBits]::One)
$serial.ReadTimeout = $ReadTimeoutMs
$response = New-Object System.Collections.Generic.List[byte]
$exitCode = 0

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

function Format-Hex([System.Collections.Generic.List[byte]]$bytes) {
  if (($null -eq $bytes) -or ($bytes.Count -eq 0)) {
    return ""
  }
  return [string]::Join(" ", ($bytes | ForEach-Object { "{0:X2}" -f $_ }))
}

function Format-Request([byte[]]$bytes) {
  return [string]::Join(" ", ($bytes | ForEach-Object { "{0:X2}" -f $_ }))
}

try {
  $serial.Open()
  $serial.DiscardInBuffer()
  $serial.DiscardOutBuffer()
  Append-Utf8 $LogPath ("[{0}] [diag] start port={1} baud={2} backend=powershell" -f (Get-Timestamp), $Port, $Baudrate)
  Append-Utf8 $LogPath ("[{0}] > {1}" -f (Get-Timestamp), (Format-Request $request))
  $serial.Write($request, 0, $request.Length)

  $deadline = [DateTime]::UtcNow.AddMilliseconds($ResponseTimeoutMs)
  $lastByteAt = $null
  while ([DateTime]::UtcNow -lt $deadline) {
    try {
      $next = $serial.ReadByte()
      if ($next -ge 0) {
        $response.Add([byte]$next)
        $lastByteAt = [DateTime]::UtcNow
        if (($ExpectedLength -gt 0) -and ($response.Count -ge $ExpectedLength)) {
          break
        }
        continue
      }
    } catch [System.TimeoutException] {
    }

    if (($response.Count -gt 0) -and ($null -ne $lastByteAt)) {
      if (([DateTime]::UtcNow - $lastByteAt).TotalMilliseconds -ge $SilenceTimeoutMs) {
        break
      }
    }
  }

  if ($response.Count -gt 0) {
    Append-Utf8 $LogPath ("[{0}] < {1}" -f (Get-Timestamp), (Format-Hex $response))
  } else {
    Append-Utf8 $LogPath ("[{0}] < [timeout]" -f (Get-Timestamp))
    $exitCode = 41
  }
} finally {
  if ($serial.IsOpen) {
    $serial.Close()
  }
  Append-Utf8 $LogPath ("[{0}] [diag] stop" -f (Get-Timestamp))
}

[ordered]@{
  exit_code = $exitCode
  response_hex = (Format-Hex $response)
} | ConvertTo-Json -Depth 4 | Set-Content -Path $ResultFile -Encoding UTF8
