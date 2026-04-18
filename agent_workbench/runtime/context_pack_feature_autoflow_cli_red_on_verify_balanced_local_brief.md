# Local Model Brief

- mode: `feature`
- stage: `verify`
- profile: `balanced_local`
- F01: project = serial
- F02: mode_stage_profile = feature/verify/balanced_local
- F03: uart_contract = COM3 @ 115200 ready=STM32 UART CLI ready. prompt=cli>
- F04: task_id = autoflow_cli_red_on
- F05: task_goal = 请通过 CLI 点亮红灯
- F06: task_verify_commands = red on, status
- F06B: task_max_edit_files = 0
- F13: current_subtasks = S3, S4

## Current Subtasks
- S3: Run the UART CLI command.
- objective: Execute the exact UART command and capture transcript evidence.
- S4: Report from transcript evidence only.
- objective: Use the transcript and diagnostics to report pass, fail, blocked, or needs_review.

## Allowed Reads
- `H:\stm32_RAG\code\serial\agent_workbench\generated\requests\cli_20260412_200632\task_draft.yaml`
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
- `cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command ""red on"" --command ""status"""`
