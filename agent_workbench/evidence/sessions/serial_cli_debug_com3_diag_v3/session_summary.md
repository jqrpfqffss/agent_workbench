# Session Summary

- generated_at: 2026-04-08T11:37:05.055+00:00
- session_dir: `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_debug_com3_diag_v3`
- verdict: `fail`
- verdict_file: `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_debug_com3_diag_v3\session_verdict.json`
- brief_file: `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_debug_com3_diag_v3\session_brief.md`
- next_step: Use the diagnostic code to pick the smallest fix before rerunning verify.

## Evidence Files
- session_manifest.json: exists
- session_verdict.json: exists
- session_brief.md: exists
- commands.log: exists
- doctor_report.md: exists
- feature_summary.md: missing
- cli_transcript.log: exists
- cli_diag.json: exists
- assertions.jsonl: missing
- compare_brief.md: missing

## Verdict Snapshot
- summary: CLI diagnostics unavailable
- strongest_evidence: OpenOCD or DebugCliStats symbol could not be read.
- assertions: pass=0 fail=0 skip=0

## CLI Diagnostics
- status: error
- code: diag_unavailable
- summary: CLI diagnostics unavailable
- detail: OpenOCD or DebugCliStats symbol could not be read.

## Failed Assertions
- none

## CLI Tail
- [2026-04-06T10:15:59.306+00:00] [cli] reset-first exit=0
- [2026-04-06T10:15:59.810+00:00] [cli] start port=COM3 baud=115200 expect_ready=1 reset_first=1 backend=powershell
- [2026-04-06T10:16:06.003+00:00] [cli] ready-missing expected=STM32 UART CLI ready.
- [2026-04-06T10:16:06.033+00:00] [cli] stop

## Monitor Stats
- no valid monitor samples
