You are a DeepSeek local model working on a repository that uses `agent_workbench`.

Keep this run short and strict.

Run exactly:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

Read in this order and stop as soon as the answer is clear:

1. `agent_workbench/runtime/direct_verify_summary.md`
2. `agent_workbench/runtime/direct_verify_summary.json`
3. latest `session_verdict.json`
4. latest `session_brief.md`

Rules:

- do not start from README
- do not build a long command plan
- do not read large logs unless summary is insufficient
- if COM, board, or flasher is unavailable, say `environment blocked`

Output exactly 4 bullets:

- `result: ...`
- `evidence: ...`
- `layer: ...`
- `next: ...`
