# Implementation Brief

- task_id: `add_echo_cli`
- mode: `feature`
- goal: Add a board CLI command that echoes the provided text payload on one line.
- include: Core/Src/cli.c, Core/Src/app_cli_commands.c, Core/Inc, CMakeLists.txt
- exclude: Drivers
- verify: doctor, build, test, debug
