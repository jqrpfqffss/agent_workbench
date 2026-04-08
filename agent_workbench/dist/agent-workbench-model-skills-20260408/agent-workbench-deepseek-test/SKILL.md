---
name: agent-workbench-deepseek-test
description: Use for DeepSeek-driven test generation and test execution in agent_workbench projects. Keep the flow short, task-led, and focused on generated assets and unit logs.
---

# Agent Workbench DeepSeek Test

Use this skill for test generation, test execution, or explaining test failures.

## Commands

Run only these first:

```powershell
cmd /c ".\agent_workbench.bat test generate --task <task.yaml>"
cmd /c ".\agent_workbench.bat test run"
```

## Read Order

1. `agent_workbench/runtime/unit.log`
2. `agent_workbench/generated/tasks/<task_id>/unit_test_plan.md`
3. `agent_workbench/generated/tasks/<task_id>/blackbox_assertions.yaml`

Only read source files if the user explicitly asks for a fix.

## Output Format

Use exactly:

- `result: ...`
- `assets: ...`
- `first_fail: ...`
- `next: ...`

## Guardrails

- If tests fail, name the first failing layer.
- Prefer task fixes over code fixes when the acceptance design is wrong.
- Keep answers short and operational.
