# Implementation Brief

- task_id: `timer_led_blink`
- mode: `feature`
- goal: Add a hardware timer (TIM3) that blinks the RED LED (PB0) at approximately 1 Hz using interrupt-driven toggling.
- include: Core/Src/main.c, Core/Src/stm32f1xx_it.c, Core/Inc/main.h
- exclude: Drivers, Core/Src/cli.c, Core/Src/app_cli_commands.c
- verify: doctor, build, uart_smoke
- read_candidates: Core/Src/main.c, Core/Src/stm32f1xx_it.c, Core/Inc/main.h
- edit_candidates: Core/Src/main.c, Core/Src/stm32f1xx_it.c, Core/Inc/main.h
- stable_strings: STM32 UART CLI ready., Available commands:, All existing CLI command names and help text
- max_edit_files: 3
