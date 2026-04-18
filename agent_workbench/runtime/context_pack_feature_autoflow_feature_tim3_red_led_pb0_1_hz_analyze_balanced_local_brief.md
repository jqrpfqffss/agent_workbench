# Local Model Brief

- mode: `feature`
- stage: `analyze`
- profile: `balanced_local`
- F01: project = serial
- F02: mode_stage_profile = feature/analyze/balanced_local
- F03: uart_contract = COM3 @ 115200 ready=STM32 UART CLI ready. prompt=cli>
- F04: task_id = autoflow_feature_tim3_red_led_pb0_1_hz
- F05: task_goal = 使用 TIM3 定时器让 RED LED(PB0) 以约 1 Hz 闪烁
- F06: task_verify_commands = help, status
- F13: current_subtasks = S1, S2

## Current Subtasks
- S1: Read the task and the latest evidence.
- objective: Confirm the goal, scope, stable strings, and the first blocking layer before planning edits.
- S2: Lock the smallest edit scope.
- objective: Choose the minimal set of files needed for this round so the model does not expand scope too early.

## Allowed Reads
- `H:\stm32_RAG\code\serial\agent_workbench\generated\requests\tim3_red_led_pb0_1_hz_20260412_131012\task_draft.yaml`
- `H:\stm32_RAG\code\serial\agent_workbench\generated\tasks\autoflow_feature_tim3_red_led_pb0_1_hz\implementation_brief.md`
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
- `cmd /c ".\agent_workbench.bat context --mode feature --stage implement --task H:/stm32_RAG/code/serial/agent_workbench/generated/requests/tim3_red_led_pb0_1_hz_20260412_131012/task_draft.yaml --profile balanced_local"`
- `Only after analysis is complete, make the smallest safe change in allowed edit files.`
