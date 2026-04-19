# Implementation Brief

- task_id: `cli_automation_regression`
- mode: `feature`
- goal: Keep the USART2 text CLI command-driven, automation-friendly, and safe for repeated debug sessions.
- include: Core/Src/cli.c, Core/Src/app_cli_commands.c, Core/Src/main.c, Core/Inc, CMakeLists.txt
- exclude: Drivers
- verify: doctor, build, test, debug
- read_candidates: Core/Src/cli.c, Core/Src/app_cli_commands.c
- edit_candidates: Core/Src/cli.c, Core/Src/app_cli_commands.c
- stable_strings: STM32 UART CLI ready., cli>, Available commands:, UART: USART2 @ 115200 8N1, [ok] red -> on, [ok] green -> off, [ok] blue -> toggle, [ok] all -> off
- max_edit_files: 2
