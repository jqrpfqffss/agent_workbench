# OpenCode Orchestration

Use exactly two skills for most work:

- `agent-workbench-toolbox` plus `agent-workbench-feature` for feature implementation.
- `agent-workbench-toolbox` plus `agent-workbench-debug` for debugging.
- `agent-workbench-toolbox` plus `agent-workbench-test` for test design and validation.

Avoid loading all workflow skills at once. Choose the dominant user intent, then pull a second workflow only if the work changes phase.

## Default OpenCode Loop

1. Discover: `doctor --json`, `scan-project --json`.
2. Inspect: read current source, generated headers, config, and existing evidence.
3. Act: edit source or `agent_workbench/agent_workbench.yaml` when monitor coverage is needed.
4. Build: `build --json`, then narrow repair if needed.
5. Exercise hardware: flash, UART, diag, monitor.
6. Summarize: `verify current --json`, `report --latest --json`, and `compare --latest --json` when useful.
7. Report with artifact paths and unresolved risks.

## Practical Rules

- Use OpenCode's own planning ability for decomposition; do not depend on legacy planning output.
- Treat `agent_workbench/tests/*.py` as workbench self-tests only. They are useful when changing the platform itself, not when validating a migrated STM32 firmware feature.
- For migrated projects, prefer source discovery plus runtime evidence over repository-specific generated assets.
- If monitor evidence is necessary, OpenCode should update YAML automatically and validate with `monitor probe`.
- If evidence conflicts with source expectations, trust evidence first and design the next narrow probe.
