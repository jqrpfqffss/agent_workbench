You are working in a repository that uses `agent_workbench`.

Follow these rules exactly:

1. Use only PowerShell-safe batch invocation:
   `cmd /c ".\\agent_workbench.bat <subcommand> ..."`
2. Never use `cd ... && ...`
3. Never use bare `.bat` commands in PowerShell
4. Never create long manual shell chains when one workbench command already exists
5. Read summary evidence before raw logs

Task handling:

- If the user provided a task yaml, use it.
- Otherwise choose the closest task under `agent_workbench/tasks/`.
- State the chosen task path in one short sentence.

Preferred current-state validation:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

Then read only:

- `agent_workbench/runtime/direct_verify_summary.md`
- `agent_workbench/runtime/direct_verify_summary.json`

Only if needed, read:

- latest `session_verdict.json`
- latest `session_brief.md`

Guardrails:

- Evidence before edits
- If `doctor`, `build`, or `test run` fails, stop at that layer
- If UART or COM is missing, report environment blocking
- Do not invent results that are not in evidence

Output in this order:

1. `result: ...`
2. `evidence: ...`
3. `failure_layer: ...`
4. `next: ...`
