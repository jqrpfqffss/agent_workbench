# Implementation Brief

- task_id: `autoflow_feature_task`
- mode: `feature`
- goal: 点亮红灯
- include: Core/Src/main.c
- exclude: Drivers
- verify: doctor, build, uart_smoke
- read_candidates: Core/Src/main.c
- edit_candidates: Core/Src/main.c
- stable_strings: STM32 UART CLI ready., cli>, Available commands:
- max_edit_files: 2
