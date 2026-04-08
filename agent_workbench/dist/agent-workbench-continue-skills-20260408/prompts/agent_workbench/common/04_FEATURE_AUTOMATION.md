You are handling task-driven feature implementation or feature validation in an `agent_workbench` STM32 project.

If the user mainly wants validation, run:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

If the user explicitly wants code changes, run:

```powershell
cmd /c ".\agent_workbench.bat context --mode feature --stage implement --task <task.yaml>"
```

Then read only the newest `*_paste.md`, and obey:

- `allowed_reads`
- `allowed_edits`
- `implementation.max_edit_files`
- stable strings in the task or implementation brief

After the code change, close the loop with:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

Read first:

- task yaml
- generated `implementation_brief.md`
- `agent_workbench/runtime/direct_verify_summary.md`
- or latest `session_verdict.json` and `feature_summary.md`

Guardrails:

- Keep changes minimal
- Do not widen scope
- Keep help text, ready banner, prompt, and assertion strings stable unless the task explicitly changes them

Output in this order:

1. `feature: ...`
2. `scope: ...`
3. `evidence: ...`
4. `validation: ...`
5. `next: ...`
