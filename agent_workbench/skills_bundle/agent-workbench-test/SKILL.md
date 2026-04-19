---
name: agent-workbench-test
description: Use for automated test generation, test execution, task-driven test asset updates, and evidence-first test reporting in agent_workbench STM32 projects.
---

# Agent Workbench Test

Use this skill when the user wants to generate tests, run tests, improve test assets, or explain test failures in a repo that uses `agent_workbench`.

## First Step

Resolve the task yaml first. Then run:

```powershell
cmd /c ".\agent_workbench.bat test generate --task <task.yaml>"
cmd /c ".\agent_workbench.bat test run"
```

If the model is low-context or the task is complex, generate a staged card first:

```powershell
cmd /c ".\agent_workbench.bat context --mode test --stage analyze --task <task.yaml>"
```

Then read only the newest `*_paste.md`.

## Read These Files

Read only the test-relevant artifacts first:

- `agent_workbench/generated/tasks/<task_id>/blackbox_assertions.yaml`
- `agent_workbench/generated/tasks/<task_id>/unit_test_plan.md`
- `agent_workbench/generated/tasks/<task_id>/implementation_brief.md`
- `agent_workbench/generated/tasks/<task_id>/task_snapshot.json`
- `agent_workbench/runtime/unit.log`

## What To Change First

If the test design is wrong:

- update the task yaml
- regenerate tests
- rerun tests

If the task yaml is correct but generated assets are too weak:

- improve the task yaml or generated test artifacts first
- do not immediately blame source files

If the source really violates the task acceptance:

- only then coordinate with the feature flow

## Guardrails

- Keep assertions stable and machine-readable.
- Prefer short deterministic strings over vague output matching.
- Report whether the failure is in task definition, test assets, or source behavior.
- Do not edit broad production code during a test-only request unless the user explicitly asks for a fix.

## Default Output

Respond in this order:

1. Test result
2. Generated assets used
3. First failing layer
4. Recommended next action
