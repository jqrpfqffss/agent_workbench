---
name: agent-workbench-qwen-feature
description: Use for Qwen-driven feature implementation or validation in agent_workbench projects, with minimal edits, staged cards, and direct verify for closure.
---

# Agent Workbench Qwen Feature

Use this skill when the work is defined by a task yaml.

## Validation Path

If the request is mainly validation:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

## Implementation Path

If the user explicitly requests code changes:

```powershell
cmd /c ".\agent_workbench.bat context --mode feature --stage implement --task <task.yaml>"
```

Then read only the newest `*_paste.md`.

After the change, close the loop with:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

## Read Priority

1. task yaml
2. generated `implementation_brief.md`
3. `direct_verify_summary.md` or latest `session_verdict.json`

## Output Format

Use:

- `feature: ...`
- `scope: ...`
- `evidence: ...`
- `validation: ...`
- `next: ...`

## Guardrails

- Respect `allowed_edits`.
- Keep stable strings stable.
- Prefer direct verify over long manual command sequences.
