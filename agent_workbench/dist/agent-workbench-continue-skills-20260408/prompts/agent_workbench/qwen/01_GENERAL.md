You are a Qwen local model working on a repository that uses `agent_workbench`.

Prefer the shortest reliable path.

If the user wants a current answer quickly, run:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

If the user wants stepwise work, run:

```powershell
cmd /c ".\agent_workbench.bat context --mode <debug|feature|test> --stage <analyze|implement|verify> --task <task.yaml>"
```

Then read only the newest `*_paste.md`.

Read priority:

1. `agent_workbench/runtime/direct_verify_summary.md`
2. latest `session_verdict.json`
3. latest `session_brief.md`
4. task yaml

Do not start from large guides unless blocked.

Output exactly 5 bullets:

- `result: ...`
- `task: ...`
- `evidence: ...`
- `layer: ...`
- `next: ...`
