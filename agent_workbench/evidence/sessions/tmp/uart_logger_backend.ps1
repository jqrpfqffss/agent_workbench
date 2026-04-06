param(
  [string]$Port,
  [int]$Baudrate,
  [string]$LogPath,
  [int]$ReadTimeoutMs
)
$ErrorActionPreference = "Stop"
$serial = New-Object System.IO.Ports.SerialPort $Port, $Baudrate, ([System.IO.Ports.Parity]::None), 8, ([System.IO.Ports.StopBits]::One)
$serial.Encoding = [System.Text.Encoding]::UTF8
$serial.NewLine = "`n"
$serial.ReadTimeout = $ReadTimeoutMs
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
try {
  $serial.Open()
  Append-Utf8 $LogPath ("[{0}] [uart] start port={1} baud={2} backend=powershell" -f (Get-Timestamp), $Port, $Baudrate)
  while ($true) {
    try {
      $line = $serial.ReadLine().TrimEnd("`r", "`n")
      Append-Utf8 $LogPath ("[{0}] {1}" -f (Get-Timestamp), $line)
    } catch [System.TimeoutException] {
      continue
    }
  }
} finally {
  if ($serial.IsOpen) {
    $serial.Close()
  }
}
