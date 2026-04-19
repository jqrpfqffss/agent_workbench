# Local Model Brief

- mode: `feature`
- stage: `resume`
- profile: `balanced_local`
- F01: project = serial
- F02: mode_stage_profile = feature/resume/balanced_local
- F03: uart_contract = COM3 @ 115200 ready=STM32 UART CLI ready. prompt=cli>
- F04: task_id = cli_automation_regression
- F05: task_goal = Keep the USART2 text CLI command-driven, automation-friendly, and safe for repeated debug sessions.
- F06: task_verify_commands = help, status, red on, green off, blue toggle, all off
- F07: latest_session = serial_cli_feature_com3_diag_v2
- F08: verdict_status = fail
- F09: verdict_summary = 9 black-box assertions failed.
- F10: strongest_evidence = cli_ready_banner_seen | STM32 UART CLI ready.
- F11: cli_diag_code = rx_zero
- F12: assertion_counts = pass=1 fail=9 skip=0

## Allowed Reads
- `H:\stm32_RAG\code\serial\agent_workbench\runtime\agent_state.json`
- `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_feature_com3_diag_v2\session_brief.md`
- `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_feature_com3_diag_v2\session_verdict.json`
- `H:\stm32_RAG\code\serial\agent_workbench\tasks\cli_automation_regression.yaml`

## Allowed Edits
- none

## Unknowns
- No blocking unknowns are currently recorded.

## Forbidden Assumptions
- Do not conclude from source inspection alone.
- Do not read the whole repo when the brief already names the next files.
- Do not invent evidence that is not present in facts or session artifacts.

## CLI Tail
- [2026-04-06T10:15:09.538+00:00] [cli] reset-first exit=0
- [2026-04-06T10:15:10.037+00:00] [cli] start port=COM3 baud=115200 expect_ready=1 reset_first=1 backend=powershell
- [2026-04-06T10:15:16.221+00:00] [cli] ready-missing expected=STM32 UART CLI ready.
- [2026-04-06T10:15:16.252+00:00] [cli] stop

## Next Commands
- `agent_workbench.bat context --mode feature --stage analyze --task H:/stm32_RAG/code/serial/agent_workbench/tasks/cli_automation_regression.yaml --profile balanced_local`
