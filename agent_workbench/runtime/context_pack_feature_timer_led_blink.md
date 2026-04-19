# Local Model Brief

- mode: `feature`
- stage: `implement`
- profile: `balanced_local`
- F01: project = serial
- F02: mode_stage_profile = feature/implement/balanced_local
- F03: uart_contract = COM3 @ 115200 ready=STM32 UART CLI ready. prompt=cli>
- F04: task_id = timer_led_blink
- F05: task_goal = Add a hardware timer (TIM3) that blinks the RED LED (PB0) at approximately 1 Hz using interrupt-driven togg...
- F06: task_verify_commands = help, status
- F07: latest_session = local_model_max_validation
- F08: verdict_status = fail
- F09: verdict_summary = Firmware flash step failed.
- F10: strongest_evidence = flash_done code=1
- F12: assertion_counts = pass=1 fail=9 skip=0

## Allowed Reads
- `H:\stm32_RAG\code\serial\agent_workbench\tasks\timer_led_blink.yaml`
- `H:\stm32_RAG\code\serial\agent_workbench\generated\tasks\timer_led_blink\implementation_brief.md`
- `H:\stm32_RAG\code\serial\Core\Src\main.c`
- `H:\stm32_RAG\code\serial\Core\Src\stm32f1xx_it.c`

## Allowed Edits
- `H:\stm32_RAG\code\serial\Core\Src\main.c`
- `H:\stm32_RAG\code\serial\Core\Src\stm32f1xx_it.c`
- `H:\stm32_RAG\code\serial\Core\Inc\main.h`

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
- `agent_workbench.bat context --mode feature --stage verify --task H:/stm32_RAG/code/serial/agent_workbench/tasks/timer_led_blink.yaml --profile balanced_local`
