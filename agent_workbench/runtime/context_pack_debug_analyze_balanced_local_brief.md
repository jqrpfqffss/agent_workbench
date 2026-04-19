# Local Model Brief

- mode: `debug`
- stage: `analyze`
- profile: `balanced_local`
- F01: project = serial
- F02: mode_stage_profile = debug/analyze/balanced_local
- F03: uart_contract = COM3 @ 115200 ready=STM32 UART CLI ready. prompt=cli>
- F07: latest_session = serial_cli_debug_com3_diag_v3
- F08: verdict_status = fail
- F09: verdict_summary = CLI diagnostics unavailable
- F10: strongest_evidence = OpenOCD or DebugCliStats symbol could not be read.
- F11: cli_diag_code = diag_unavailable
- F12: assertion_counts = pass=0 fail=0 skip=0

## Allowed Reads
- `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_debug_com3_diag_v3\session_brief.md`
- `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_debug_com3_diag_v3\session_summary.md`
- `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_debug_com3_diag_v3\cli_diag.json`
- `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_debug_com3_diag_v3\assertions.jsonl`
- `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_debug_com3_diag_v3\cli_transcript.log`

## Allowed Edits
- none

## Unknowns
- No task yaml is attached to this stage.

## Forbidden Assumptions
- Do not conclude from source inspection alone.
- Do not read the whole repo when the brief already names the next files.
- Do not invent evidence that is not present in facts or session artifacts.

## CLI Tail
- [2026-04-06T10:15:59.306+00:00] [cli] reset-first exit=0
- [2026-04-06T10:15:59.810+00:00] [cli] start port=COM3 baud=115200 expect_ready=1 reset_first=1 backend=powershell
- [2026-04-06T10:16:06.003+00:00] [cli] ready-missing expected=STM32 UART CLI ready.
- [2026-04-06T10:16:06.033+00:00] [cli] stop

## Next Commands
- `agent_workbench.bat context --mode debug --stage implement --profile balanced_local`
- `Only after analysis is complete, make the smallest safe change in allowed edit files.`
