param(
  [string]$Port,
  [int]$Baudrate,
  [string]$TranscriptPath,
  [string]$CommandFile,
  [string]$ResultFile,
  [string]$ResetCommand,
  [string]$ReadyBanner,
  [string]$Prompt,
  [int]$ReadTimeoutMs,
  [int]$StartupDrainMs,
  [int]$ReadyTimeoutMs,
  [int]$CommandTimeoutMs,
  [int]$RequireReady,
  [int]$ResetFirst
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$commands = Get-Content -Raw -Path $CommandFile -Encoding UTF8 | ConvertFrom-Json
$serial = New-Object System.IO.Ports.SerialPort $Port, $Baudrate, ([System.IO.Ports.Parity]::None), 8, ([System.IO.Ports.StopBits]::One)
$serial.Encoding = [System.Text.Encoding]::UTF8
$serial.NewLine = "`n"
$serial.ReadTimeout = $ReadTimeoutMs
$transcript = New-Object System.Collections.Generic.List[string]
$timeoutCommands = New-Object System.Collections.Generic.List[string]
$script:exitCode = 0
$script:sawReady = $false
$script:sawPrompt = $false
$script:promptCount = 0
$script:pendingText = ""

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

function Write-TranscriptLine([string]$line) {
  Append-Utf8 $TranscriptPath $line
}

function Add-Rx([string]$text) {
  $transcript.Add($text)
  Write-TranscriptLine ("[{0}] < {1}" -f (Get-Timestamp), $text)
  if ($ReadyBanner -and $text.Contains($ReadyBanner)) {
    $script:sawReady = $true
  }
  if ($Prompt -and $text.Trim() -eq $Prompt.Trim()) {
    $script:sawPrompt = $true
    $script:promptCount += 1
  }
}

function Read-ChunkSafe {
  try {
    if ($serial.BytesToRead -gt 0) {
      $text = $serial.ReadExisting()
      if (-not [string]::IsNullOrEmpty($text)) {
        return $text
      }
    }
    $charCode = $serial.ReadChar()
    if ($charCode -ge 0) {
      return [string][char]$charCode
    }
  } catch [System.TimeoutException] {
    return $null
  }
}

function Flush-PendingText {
  $tail = $script:pendingText.TrimEnd("`r", "`n")
  if (-not [string]::IsNullOrWhiteSpace($tail)) {
    Add-Rx $tail
  }
  $script:pendingText = ""
}

function Process-PendingText {
  while ($true) {
    $newlineIndex = $script:pendingText.IndexOf("`n")
    $promptIndex = if ([string]::IsNullOrEmpty($Prompt)) { -1 } else { $script:pendingText.IndexOf($Prompt) }

    if (($promptIndex -ge 0) -and (($newlineIndex -lt 0) -or ($promptIndex -lt $newlineIndex))) {
      $prefix = $script:pendingText.Substring(0, $promptIndex).TrimEnd("`r")
      if (-not [string]::IsNullOrWhiteSpace($prefix)) {
        Add-Rx $prefix
      }
      $promptEnd = $promptIndex + $Prompt.Length
      while (($promptEnd -lt $script:pendingText.Length) -and ($script:pendingText[$promptEnd] -eq ' ')) {
        $promptEnd += 1
      }
      Add-Rx $Prompt.Trim()
      $script:pendingText = $script:pendingText.Substring($promptEnd)
      continue
    }

    if ($newlineIndex -lt 0) {
      break
    }

    $line = $script:pendingText.Substring(0, $newlineIndex).TrimEnd("`r")
    $script:pendingText = $script:pendingText.Substring($newlineIndex + 1)
    if ($line.Length -gt 0) {
      Add-Rx $line
    }
  }
}

function Pump-Serial {
  $chunk = Read-ChunkSafe
  if ([string]::IsNullOrEmpty($chunk)) {
    return $false
  }
  $script:pendingText += $chunk
  Process-PendingText
  return $true
}

function Drain-ForMs([int]$durationMs) {
  if ($durationMs -le 0) {
    return
  }
  $deadline = [DateTime]::UtcNow.AddMilliseconds($durationMs)
  while ([DateTime]::UtcNow -lt $deadline) {
    [void](Pump-Serial)
  }
  Flush-PendingText
}

function Invoke-ResetCommand {
  if ([string]::IsNullOrWhiteSpace($ResetCommand)) {
    return 0
  }
  $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/d", "/c", $ResetCommand -Wait -NoNewWindow -PassThru
  return [int]$proc.ExitCode
}

function Wait-Ready {
  $deadline = [DateTime]::UtcNow.AddMilliseconds($ReadyTimeoutMs)
  while ([DateTime]::UtcNow -lt $deadline) {
    [void](Pump-Serial)
    if ($script:sawReady -and $script:sawPrompt) {
      return
    }
  }
  Flush-PendingText
  if (-not $script:sawReady) {
    $script:exitCode = 31
    Write-TranscriptLine ("[{0}] [cli] ready-missing expected={1}" -f (Get-Timestamp), $ReadyBanner)
  } elseif (-not $script:sawPrompt) {
    $script:exitCode = 32
    Write-TranscriptLine ("[{0}] [cli] prompt-missing expected={1}" -f (Get-Timestamp), $Prompt)
  }
}

function Run-CommandLoop {
  foreach ($command in $commands) {
    Write-TranscriptLine ("[{0}] > {1}" -f (Get-Timestamp), $command)
    $serial.Write($command + "`r`n")
    $deadline = [DateTime]::UtcNow.AddMilliseconds($CommandTimeoutMs)
    $startPromptCount = $script:promptCount
    $hadAnyData = $false
    while ([DateTime]::UtcNow -lt $deadline) {
      if (Pump-Serial) {
        $hadAnyData = $true
      }
      if ($script:promptCount -gt $startPromptCount) {
        break
      }
    }
    Flush-PendingText
    if (-not $hadAnyData) {
      $timeoutCommands.Add($command)
      Write-TranscriptLine ("[{0}] < [timeout]" -f (Get-Timestamp))
      $script:exitCode = 33
      return
    }
    if ($script:promptCount -le $startPromptCount) {
      $timeoutCommands.Add($command)
      Write-TranscriptLine ("[{0}] [cli] prompt-missing-after-command command={1}" -f (Get-Timestamp), $command)
      $script:exitCode = 34
      return
    }
  }
}

try {
  $serial.Open()
  $serial.DiscardInBuffer()
  $serial.DiscardOutBuffer()
  Write-TranscriptLine ("[{0}] [cli] start port={1} baud={2} expect_ready={3} reset_first={4} backend=powershell" -f (Get-Timestamp), $Port, $Baudrate, $RequireReady, $ResetFirst)
  Drain-ForMs $StartupDrainMs
  if ($ResetFirst -eq 1) {
    $script:sawReady = $false
    $script:sawPrompt = $false
    $script:promptCount = 0
    $script:pendingText = ""
    $resetExit = Invoke-ResetCommand
    Write-TranscriptLine ("[{0}] [cli] reset-first exit={1}" -f (Get-Timestamp), $resetExit)
    if ($resetExit -ne 0) {
      $script:exitCode = if ($resetExit -eq 0) { 30 } else { [int]$resetExit }
    }
  }
  if (($script:exitCode -eq 0) -and ($RequireReady -eq 1)) {
    Wait-Ready
  }
  if ($script:exitCode -eq 0) {
    Run-CommandLoop
  }
} finally {
  if ($serial.IsOpen) {
    $serial.Close()
  }
  Write-TranscriptLine ("[{0}] [cli] stop" -f (Get-Timestamp))
}

[ordered]@{
  exit_code = $script:exitCode
  transcript_lines = @($transcript)
  saw_ready = $script:sawReady
  saw_prompt = $script:sawPrompt
  timeout_commands = @($timeoutCommands)
} | ConvertTo-Json -Depth 4 | Set-Content -Path $ResultFile -Encoding UTF8
