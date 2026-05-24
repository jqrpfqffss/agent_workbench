param(
  [string]$TaskFile,
  [string]$AttemptDir,
  [string]$Attempt
)

Set-Content -Path ".\tracked.txt" -Value "dirty no cleanup attempt $Attempt" -Encoding UTF8
Set-Content -Path ".\no_cleanup_new.txt" -Value "left by no-git-cleanup" -Encoding UTF8
Write-Output "no-cleanup helper ran for $TaskFile in $AttemptDir"
exit 7
