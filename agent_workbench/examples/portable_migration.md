# Portable Migration Example

This is the shortest practical checklist for moving `agent_workbench` into another STM32 project.

## Copy These Files

Required:

- `agent_workbench/`
- `agent_workbench.bat`

Recommended:

- `setup_workbench.bat`

Do not rely on old generated files from the source project as the final result:

- `AGENTS.md`
- `opencode.json`
- `.opencode/`
- `.continue/`

Regenerate them after updating the new project's config.

## Minimum Migration Steps

1. Copy the files above into the target project root.
2. Edit `agent_workbench/agent_workbench.yaml`.
3. Update at least:
   - `project.name`
   - `project.build_dir`
   - `project.artifact_file` (or legacy `project.artifact_elf`)
   - `project.compile_commands`
   - `project.source_dirs`
   - `tools.cmake.toolchain_file`
   - `tools.openocd.config_files`
   - `monitor.openocd.connect_commands`
   - `uart.*`
   - `diag_uart.*`
4. Run:

```powershell
.\setup_workbench.bat
cmd /c ".\agent_workbench.bat doctor --json"
cmd /c ".\agent_workbench.bat build --json"
cmd /c ".\agent_workbench.bat scan-project --json"
cmd /c ".\agent_workbench.bat test run --json"
cmd /c ".\agent_workbench.bat integration install opencode --json"
cmd /c ".\agent_workbench.bat integration check opencode --json"
```

5. If needed, also run:

```powershell
cmd /c ".\agent_workbench.bat integration install continue --json"
cmd /c ".\agent_workbench.bat integration check continue --json"
```

6. If the project has UART CLI, validate it with:

```powershell
cmd /c ".\agent_workbench.bat uart exec --expect-ready --command help --command status --json"
```

7. If the project has no CLI or diag UART, disable them in `agent_workbench.yaml` instead of leaving sample values in place.

## Practical Notes

- `project.root` usually stays `..` if `agent_workbench/` is placed under the target project root.
- `artifact_file`, `compile_commands`, and `monitor.symbols.path` should all match the same real build output family.
- `.elf` and `.axf` are both fine as long as `arm-none-eabi-nm` can parse the file.
- Monitor portability should come from YAML: `tools.openocd.config_files`, optional `monitor.openocd.connect_commands`, and `monitor.items`.
- If you change `project.name`, `ready_banner`, `prompt`, or `source_dirs`, rerun `integration install`.
- The current build pipeline expects a CMake-based STM32 project.

For the full beginner-friendly Chinese guide, read:

- `agent_workbench/MIGRATION_GUIDE_ZH.md`
