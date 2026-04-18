# Local Model Brief

- mode: `feature`
- stage: `implement`
- profile: `balanced_local`
- F01: project = serial
- F02: mode_stage_profile = feature/implement/balanced_local
- F03: uart_contract = COM3 @ 115200 ready=STM32 UART CLI ready. prompt=cli>
- F04: task_id = autoflow_feature_tim3_red_led_pb0_1_hz
- F05: task_goal = 使用 TIM3 定时器让 RED LED(PB0) 以约 1 Hz 闪烁
- F06: task_verify_commands = help, status
- F13: current_subtasks = S3, S4

## Current Subtasks
- S3: Implement the feature only in allowed files.
- objective: Apply the smallest code change that satisfies the task goal without widening scope.
- S4: Pass local build and automation checks first.
- objective: Confirm build and local checks are healthy before running the full hardware validation loop.

## Allowed Reads
- `H:\stm32_RAG\code\serial\agent_workbench\generated\requests\tim3_red_led_pb0_1_hz_20260412_131012\task_draft.yaml`
- `H:\stm32_RAG\code\serial\agent_workbench\generated\tasks\autoflow_feature_tim3_red_led_pb0_1_hz\implementation_brief.md`
- `H:\stm32_RAG\code\serial\agent_workbench\generated\tasks\autoflow_feature_tim3_red_led_pb0_1_hz\task_breakdown.md`
- `H:\stm32_RAG\code\serial\Core\Src\main.c`
- `H:\stm32_RAG\code\serial\Core\Src\stm32f1xx_it.c`

## Allowed Edits
- `H:\stm32_RAG\code\serial\Core\Src\main.c`
- `H:\stm32_RAG\code\serial\Core\Src\stm32f1xx_it.c`
- `H:\stm32_RAG\code\serial\Core\Inc\stm32f1xx_hal_conf.h`

## Unknowns
- No matching evidence session is available.
- The current verdict is incomplete and may require one more validation pass.

## Forbidden Assumptions
- Do not conclude from source inspection alone.
- Do not read the whole repo when the brief already names the next files.
- Do not invent evidence that is not present in facts or session artifacts.

## Next Commands
- `cmd /c ".\agent_workbench.bat build"`
- `cmd /c ".\agent_workbench.bat test run"`
- `cmd /c ".\agent_workbench.bat context --mode feature --stage verify --task H:/stm32_RAG/code/serial/agent_workbench/generated/requests/tim3_red_led_pb0_1_hz_20260412_131012/task_draft.yaml --profile balanced_local"`
