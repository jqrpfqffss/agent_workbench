# Implementation Brief

- task_id: `add_led_status_cli`
- mode: `feature`
- goal: Add a CLI command 'led_status' that prints the on/off state of all three LEDs (RED, GREEN, BLUE) on the board.
- include: Core/Src/app_cli_commands.c, Core/Inc/app_cli_commands.h, agent_workbench/agent_workbench.yaml
- exclude: Drivers
- verify: doctor, build, test, uart exec, session feature, compare
