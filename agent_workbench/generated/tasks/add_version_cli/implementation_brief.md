# Implementation Brief

- task_id: `add_version_cli`
- mode: `feature`
- goal: Add a board CLI command that reports firmware version and build profile.
- include: Core/App/cli, Core/App/Tasks, CMakeLists.txt
- exclude: Drivers, Middlewares
- verify: doctor, build, test, debug
