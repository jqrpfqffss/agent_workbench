# Local Model Brief

- mode: `feature`
- stage: `analyze`
- profile: `balanced_local`
- F01: project = serial
- F02: mode_stage_profile = feature/analyze/balanced_local
- F03: uart_contract = COM3 @ 115200 ready=STM32 UART CLI ready. prompt=cli>
- F04: task_id = autoflow_cli_red_on
- F05: task_goal = 请通过 CLI 点亮红灯
- F06: task_verify_commands = red on, status
- F06B: task_max_edit_files = 0
- F13: current_subtasks = S1, S2

## Current Subtasks
- S1: Confirm the exact existing CLI command.
- objective: Map the natural-language goal to a built-in UART CLI command without inventing code work.
- S2: Lock the verify-only path.
- objective: Confirm that no code edits are required and the next round should jump directly to verification.

## Allowed Reads
- `H:\stm32_RAG\code\serial\agent_workbench\generated\requests\cli_20260412_200632\task_draft.yaml`
- `H:\stm32_RAG\code\serial\agent_workbench\generated\tasks\autoflow_cli_red_on\implementation_brief.md`
- `H:\stm32_RAG\code\serial\agent_workbench\generated\tasks\autoflow_cli_red_on\task_breakdown.md`

## Allowed Edits
- none

## Unknowns
- No matching evidence session is available.
- The current verdict is incomplete and may require one more validation pass.

## Forbidden Assumptions
- Do not conclude from source inspection alone.
- Do not read the whole repo when the brief already names the next files.
- Do not invent evidence that is not present in facts or session artifacts.

## Next Commands
- `cmd /c ".\agent_workbench.bat context --mode feature --stage verify --task H:/stm32_RAG/code/serial/agent_workbench/generated/requests/cli_20260412_200632/task_draft.yaml --profile balanced_local"`
- `cmd /c ".\agent_workbench.bat autoflow --resume"`
