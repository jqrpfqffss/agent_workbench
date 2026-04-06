# Continue Feature Prompt

Read:

- `agent_workbench/agent_workbench.yaml`
- the task file passed to `session feature`
- generated files under `agent_workbench/generated/tasks/<task_id>/`

Your job:

1. Implement the feature inside the allowed scope.
2. Add or update observability hooks, CLI commands, or monitor points when the task asks for them.
3. Keep changes small and verifiable.
4. Prefer validating board behavior through `flash`, `uart exec --reset-first --expect-ready`, and `session feature`.
5. Use `cli_transcript.log` and `cli_diag.json` as first-class evidence, not just passive UART logs.
6. Run `agent_workbench.bat session feature --task <task.yaml>`.
7. Update the report with the exact evidence used to accept or reject the change.
