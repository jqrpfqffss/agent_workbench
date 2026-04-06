# Implementation Brief

- task_id: `cli_automation_regression`
- mode: `feature`
- goal: Keep the USART2 text CLI command-driven, automation-friendly, and safe for repeated debug sessions.
- include: Core/Src/cli.c, Core/Src/app_cli_commands.c, Core/Src/main.c, Core/Inc, CMakeLists.txt
- exclude: Drivers
- verify: doctor, build, test, debug
