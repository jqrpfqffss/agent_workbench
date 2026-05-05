# OpenCode Command Execution

Use this reference whenever OpenCode fails to run a workbench command or when examples still show the older wrapper form.

## Preferred Form

Run from the repository root:

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

Why this form:

- The relative path is not quoted, so PowerShell treats it as an executable command rather than a string.
- The inner batch file resolves the Python interpreter and `workbench.py`.
- It avoids the extra `cmd /c` quoting layer that frequently fails in OpenCode.

This form is invalid because it is a string followed by arguments:

```powershell
".\agent_workbench\bin\agent_workbench.bat" doctor --json
```

If the command path must be quoted, use PowerShell's call operator:

```powershell
& ".\agent_workbench\bin\agent_workbench.bat" doctor --json
```

## Fallback Forms

If the batch form fails because of quoting or launcher issues, retry with:

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

If `python` is not on PATH, try:

```powershell
py -3 ".\agent_workbench\workbench.py" doctor --json
```

Use the same replacement pattern for every subcommand.

## Rules

- Keep one command per shell call.
- Always pass `--json` when the command supports it.
- Do not chain with `;`, `&&`, or `|` in OpenCode unless the user explicitly asked for shell composition.
- Do not silently switch to unrelated scripts. The direct Python fallback is still the same `agent_workbench` public CLI.
- If both batch and Python forms fail, report the exact command, exit code, and stderr as an environment blocker.
