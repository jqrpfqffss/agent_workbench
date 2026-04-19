# Session Brief

- generated_at: 2026-04-08T11:37:05.053+00:00
- session: `serial_cli_debug_com3_diag_v3`
- status: `fail`
- summary: CLI diagnostics unavailable
- strongest_evidence: OpenOCD or DebugCliStats symbol could not be read.
- next_step: Use the diagnostic code to pick the smallest fix before rerunning verify.
- assertions: pass=0 fail=0 skip=0
- cli_diag: diag_unavailable | CLI diagnostics unavailable

## Read First
- `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_debug_com3_diag_v3\session_verdict.json`
- `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_debug_com3_diag_v3\session_summary.md`
- `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_debug_com3_diag_v3\cli_transcript.log`

## CLI Tail
- [2026-04-06T10:15:59.306+00:00] [cli] reset-first exit=0
- [2026-04-06T10:15:59.810+00:00] [cli] start port=COM3 baud=115200 expect_ready=1 reset_first=1 backend=powershell
- [2026-04-06T10:16:06.003+00:00] [cli] ready-missing expected=STM32 UART CLI ready.
- [2026-04-06T10:16:06.033+00:00] [cli] stop
