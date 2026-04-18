# Local Model Brief

- mode: `feature`
- stage: `implement`
- profile: `balanced_local`
- F01: project = serial
- F02: mode_stage_profile = feature/implement/balanced_local
- F03: uart_contract = COM3 @ 115200 ready=STM32 UART CLI ready. prompt=cli>
- F04: task_id = cli_automation_regression
- F05: task_goal = Keep the USART2 text CLI command-driven, automation-friendly, and safe for repeated debug sessions.
- F06: task_verify_commands = help, status, red on, green off, blue toggle, all off
- F07: latest_session = local_model_max_validation
- F08: verdict_status = fail
- F09: verdict_summary = Firmware flash step failed.
- F10: strongest_evidence = flash_done code=1
- F12: assertion_counts = pass=1 fail=9 skip=0
- F13: current_subtasks = S3, S4

## Current Subtasks
- S3: Implement the feature only in allowed files.
- objective: Apply the smallest code change that satisfies the task goal without widening scope.
- S4: Pass local build and automation checks first.
- objective: Confirm build and local checks are healthy before running the full hardware validation loop.

## Allowed Reads
- `H:\stm32_RAG\code\serial\agent_workbench\tasks\cli_automation_regression.yaml`
- `H:\stm32_RAG\code\serial\agent_workbench\generated\tasks\cli_automation_regression\implementation_brief.md`
- `H:\stm32_RAG\code\serial\agent_workbench\generated\tasks\cli_automation_regression\task_breakdown.md`
- `H:\stm32_RAG\code\serial\Core\Src\cli.c`
- `H:\stm32_RAG\code\serial\Core\Src\app_cli_commands.c`

## Allowed Edits
- `H:\stm32_RAG\code\serial\Core\Src\cli.c`
- `H:\stm32_RAG\code\serial\Core\Src\app_cli_commands.c`

## Unknowns
- No CLI diagnostic file exists for the selected session.

## Forbidden Assumptions
- Do not conclude from source inspection alone.
- Do not read the whole repo when the brief already names the next files.
- Do not invent evidence that is not present in facts or session artifacts.

## CLI Tail
- [2026-04-08T11:33:39.340+00:00] [cli] stop

## Next Commands
- `agent_workbench.bat build`
- `agent_workbench.bat test run`
- `agent_workbench.bat context --mode feature --stage verify --task H:/stm32_RAG/code/serial/agent_workbench/tasks/cli_automation_regression.yaml --profile balanced_local`
