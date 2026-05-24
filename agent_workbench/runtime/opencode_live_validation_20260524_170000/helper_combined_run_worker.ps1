param(
  [string]$TaskFile,
  [string]$TaskId
)

$taskText = Get-Content -Raw -Path $TaskFile
if ($taskText -like "*Combined pass one*") {
  Set-Content -Path ".\combined_pass_1.txt" -Value "pass1" -Encoding UTF8
  Write-Output "combined pass one"
  exit 0
}

if ($taskText -like "*Combined fail second*") {
  Set-Content -Path ".\combined_failed_new.txt" -Value "failed" -Encoding UTF8
  Set-Content -Path ".\tracked.txt" -Value "combined failed dirty" -Encoding UTF8
  Write-Output "combined fail second"
  exit 7
}

if ($taskText -like "*Combined pass three*") {
  if (-not (Test-Path ".\combined_pass_1.txt")) {
    Write-Error "combined_pass_1.txt is missing"
    exit 8
  }
  if (Test-Path ".\combined_failed_new.txt") {
    Write-Error "combined_failed_new.txt should have been cleaned"
    exit 9
  }
  Set-Content -Path ".\combined_pass_3.txt" -Value "pass3" -Encoding UTF8
  Write-Output "combined pass three"
  exit 0
}

Write-Error "unknown combined task $TaskId"
exit 10
