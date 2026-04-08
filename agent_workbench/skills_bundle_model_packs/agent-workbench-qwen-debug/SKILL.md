---
name: agent-workbench-qwen-debug
description: Use for Qwen-driven UART CLI debug and smoke analysis in agent_workbench projects. Prefer direct verify, then evidence-backed classification and a compact debug conclusion.
---

# Agent Workbench Qwen Debug

Use this skill for debug, smoke, or CLI interaction issues.

## Start

Run:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

If the result is unclear, use:

```powershell
cmd /c ".\agent_workbench.bat context --mode debug --stage analyze"
```

## Read Order

1. `direct_verify_summary.md`
2. latest `session_verdict.json`
3. latest `cli_diag.json`
4. latest `cli_transcript.log`

## Classification

Prefer the classification in `cli_diag.json`.

If missing, infer only from explicit evidence in:

- `direct_verify_summary.md`
- `session_verdict.json`
- `session_brief.md`

## Output Format

Use:

- `result: ...`
- `classification: ...`
- `evidence: ...`
- `layer: ...`
- `next: ...`
