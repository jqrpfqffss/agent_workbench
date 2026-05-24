param(
  [string]$TaskFile,
  [string]$AttemptDir,
  [string]$Attempt
)

$attemptNumber = [int]$Attempt
if ($attemptNumber -eq 1) {
  Set-Content -Path ".\tracked.txt" -Value "retry failed attempt" -Encoding UTF8
  Set-Content -Path ".\retry_failed_new.txt" -Value "created by failed retry" -Encoding UTF8
  Write-Output "retry helper failing attempt $Attempt from $TaskFile"
  exit 7
}

Set-Content -Path ".\retry_success.txt" -Value "passed on attempt $Attempt" -Encoding UTF8
Write-Output "retry helper passed attempt $Attempt in $AttemptDir"
exit 0
