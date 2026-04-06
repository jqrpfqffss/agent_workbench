# Implementation Brief

- task_id: `cli_hardware_smoke`
- mode: `debug`
- goal: Verify the USART3 PB10/PB11 CLI handshake, prompt, command execution, and diagnostics on real hardware.
- include: Core/App/cli, Core/App/Tasks/CliTask.c, Core/Src/usart.c, agent_workbench
- exclude: Drivers, Middlewares
- verify: doctor, build, flash, debug
