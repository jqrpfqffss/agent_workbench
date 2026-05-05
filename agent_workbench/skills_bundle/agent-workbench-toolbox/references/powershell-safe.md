# PowerShell Safe Invocation

Use one command per OpenCode shell call.

Preferred:

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
.\agent_workbench\bin\agent_workbench.bat build --json
.\agent_workbench\bin\agent_workbench.bat verify current --json
```

Fallback:

```powershell
python ".\agent_workbench\workbench.py" doctor --json
py -3 ".\agent_workbench\workbench.py" doctor --json
```

Avoid:

- `cmd /c ".\agent_workbench.bat ..."` as the default OpenCode form.
- `".\agent_workbench\bin\agent_workbench.bat" doctor --json`; that is a string followed by arguments and causes a ParserError.
- bare `agent_workbench.bat ...` in PowerShell.
- `cd ... && ...`, `;`, or pipes for normal workbench calls.
- writing JSON parsing shell pipelines when OpenCode can inspect the returned JSON directly.

Use `& ".\agent_workbench\bin\agent_workbench.bat" doctor --json` only when the command path is quoted.

If a command fails, classify whether it is a launcher problem, a workbench failure, or a hardware/environment failure before retrying.
