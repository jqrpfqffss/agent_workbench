# Implementation Brief

- task_id: `autoflow_feature_tim3_red_led_pb0_1_hz`
- mode: `feature`
- goal: 使用 TIM3 定时器让 RED LED(PB0) 以约 1 Hz 闪烁
- include: Core/Src/main.c, Core/Src/stm32f1xx_it.c, Core/Inc/stm32f1xx_hal_conf.h
- exclude: Drivers, Core/Src/cli.c, Core/Src/app_cli_commands.c
- verify: doctor, build, uart_smoke
- read_candidates: Core/Src/main.c, Core/Src/stm32f1xx_it.c, Core/Inc/stm32f1xx_hal_conf.h
- edit_candidates: Core/Src/main.c, Core/Src/stm32f1xx_it.c, Core/Inc/stm32f1xx_hal_conf.h
- stable_strings: STM32 UART CLI ready., cli>, Available commands:
- max_edit_files: 3
