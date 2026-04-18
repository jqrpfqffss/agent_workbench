# Local Model Brief

- mode: `feature`
- stage: `verify`
- profile: `balanced_local`
- F01: project = serial
- F02: mode_stage_profile = feature/verify/balanced_local
- F03: uart_contract = COM3 @ 115200 ready=STM32 UART CLI ready. prompt=cli>
- F04: task_id = autoflow_feature_tim3_red_led_pb0_1_hz
- F05: task_goal = 使用 TIM3 定时器让 RED LED(PB0) 以约 1 Hz 闪烁
- F06: task_verify_commands = help, status
- F13: current_subtasks = S5, S6

## Current Subtasks
- S5: Run task-specific validation commands.
- objective: Use the task CLI commands or session flow to confirm the user-visible behavior.
- S6: Close the loop with evidence only.
- objective: Use the latest evidence to report pass, fail, or blocked together with the smallest next step.

## Allowed Reads
- `H:\stm32_RAG\code\serial\agent_workbench\generated\requests\tim3_red_led_pb0_1_hz_20260412_131012\task_draft.yaml`
- `H:\stm32_RAG\code\serial\agent_workbench\generated\tasks\autoflow_feature_tim3_red_led_pb0_1_hz\task_breakdown.md`

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
- `cmd /c ".\agent_workbench.bat doctor"`
- `cmd /c ".\agent_workbench.bat build"`
- `cmd /c ".\agent_workbench.bat test generate --task H:/stm32_RAG/code/serial/agent_workbench/generated/requests/tim3_red_led_pb0_1_hz_20260412_131012/task_draft.yaml"`
- `cmd /c ".\agent_workbench.bat test run"`
- `cmd /c ".\agent_workbench.bat session feature --task H:/stm32_RAG/code/serial/agent_workbench/generated/requests/tim3_red_led_pb0_1_hz_20260412_131012/task_draft.yaml"`
- `cmd /c ".\agent_workbench.bat compare --latest"`
