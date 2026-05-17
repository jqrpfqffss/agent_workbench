# STM32 Agent Workbench

This workbench is intentionally small. The supported commands are:

- `doctor --json`
- `build --json`
- `fix-build --json`
- `flash --json`
- `reset --json`
- `uart exec --reset-first --json`
- `uart exec --reset-first --expect-ready --json`
- `diag exec --json`
- `monitor start --json`
- `monitor start --reset-first --json`
- `monitor stop --json`
- `monitor stats --json`
- `remote-dt build --json`
- `remote-dt execute --json`
- `remote-dt coverage --json`
- `remote-dt pipeline --json`
- `remote-dt pull-logs --json`

Run commands from the repository root:

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

If the batch launcher fails, use the direct Python entry:

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```
