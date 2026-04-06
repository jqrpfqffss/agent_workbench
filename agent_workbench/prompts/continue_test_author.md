# Continue Test Author Prompt

Read the task spec and generate verification assets that match the feature goal.

Default rules:

1. Prefer black-box assertions first.
2. Generate host-side unit test skeletons only when logic can be separated safely.
3. Keep generated tests readable and project-portable.
4. Reuse `agent_workbench/generated/tasks/<task_id>/` as the output location.
