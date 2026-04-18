# Implementation Brief

- task_id: `autoflow_cli_red_on`
- mode: `feature`
- goal: 请通过 CLI 点亮红灯
- include: none
- exclude: Drivers
- verify: uart_smoke
- read_candidates: none
- edit_candidates: none
- stable_strings: STM32 UART CLI ready., cli>, [ok] red -> on, LED RED
- max_edit_files: 0
