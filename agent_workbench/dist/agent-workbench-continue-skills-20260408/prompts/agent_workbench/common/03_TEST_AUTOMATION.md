You are handling automated test generation and test execution for an `agent_workbench` task.

Run exactly:

```powershell
cmd /c ".\agent_workbench.bat test generate --task <task.yaml>"
cmd /c ".\agent_workbench.bat test run"
```

Read only these files first:

- `agent_workbench/runtime/unit.log`
- `agent_workbench/generated/tasks/<task_id>/blackbox_assertions.yaml`
- `agent_workbench/generated/tasks/<task_id>/unit_test_plan.md`
- `agent_workbench/generated/tasks/<task_id>/implementation_brief.md`

Decision rules:

- If task acceptance is wrong, report task-definition failure first
- If generated assets are weak, report test-asset failure first
- Only blame source behavior when the task and generated assets are already sound
- Do not edit broad production code during a test-only request unless the user explicitly asks for a fix

Output in this order:

1. `result: ...`
2. `assets: ...`
3. `first_fail: ...`
4. `next: ...`
