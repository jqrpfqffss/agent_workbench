---
name: agent-workbench-deepseek-feature
description: Use for DeepSeek-driven feature implementation or feature validation in agent_workbench projects. Prefer direct verify for validation and staged implement-only flow for small scoped edits.
---

# Agent Workbench DeepSeek Feature

Use this skill when a task yaml defines the feature.

## Validation First

If the user is not explicitly asking for code changes, run:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

## Small Implementation Flow

Only if the user explicitly wants code changes:

```powershell
cmd /c ".\agent_workbench.bat context --mode feature --stage implement --task <task.yaml>"
```

Then read only the newest `*_paste.md`, edit only `allowed_edits`, and after editing run:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

## Output Format

Use exactly:

- `feature: ...`
- `scope: ...`
- `evidence: ...`
- `status: ...`
- `next: ...`

Keep each line short.

## Guardrails

- Do not widen scope.
- Do not read many source files.
- Do not use long manual validation chains if `verify current` is enough.
