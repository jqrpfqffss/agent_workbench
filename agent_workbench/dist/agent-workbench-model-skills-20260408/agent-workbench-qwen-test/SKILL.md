---
name: agent-workbench-qwen-test
description: Use for Qwen-driven automated test generation, unit-log review, and task-led test refinement in agent_workbench projects.
---

# Agent Workbench Qwen Test

Use this skill for test generation or test explanation.

## Commands

```powershell
cmd /c ".\agent_workbench.bat test generate --task <task.yaml>"
cmd /c ".\agent_workbench.bat test run"
```

## Read These Files

- `agent_workbench/runtime/unit.log`
- generated `unit_test_plan.md`
- generated `blackbox_assertions.yaml`
- generated `implementation_brief.md`

Read source only if the task explicitly becomes a fix task.

## Output Format

Use:

- `result: ...`
- `assets: ...`
- `failure: ...`
- `reason: ...`
- `next: ...`
