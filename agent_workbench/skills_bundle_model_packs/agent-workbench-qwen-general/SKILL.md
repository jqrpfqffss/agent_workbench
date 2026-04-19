---
name: agent-workbench-qwen-general
description: Use for Qwen local models on agent_workbench STM32 projects. Prefer direct verify or staged context cards, keep reads small, and answer in a compact structured format.
---

# Agent Workbench Qwen General

Use this skill when the model is Qwen and the repo uses `agent_workbench`.

## Preferred Start

If the user wants a current answer quickly, run:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

If the user wants stepwise work, use:

```powershell
cmd /c ".\agent_workbench.bat context --mode <debug|feature|test> --stage <analyze|implement|verify> --task <task.yaml>"
```

Then read only the newest `*_paste.md`.

## Read Priority

1. `direct_verify_summary.md`
2. `session_verdict.json`
3. `session_brief.md`
4. task yaml

Avoid large guides unless blocked.

## PowerShell Rule

Always use:

```powershell
cmd /c ".\agent_workbench.bat ..."
```

Do not use `&&`, bare `.bat`, or long chains.

## Output Format

Use 5 flat bullets:

- `result: ...`
- `task: ...`
- `evidence: ...`
- `layer: ...`
- `next: ...`

Each bullet should be concise.
