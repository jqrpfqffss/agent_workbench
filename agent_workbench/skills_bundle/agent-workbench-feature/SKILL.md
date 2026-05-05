---
name: agent-workbench-feature
description: Use for STM32 feature implementation or feature validation in repositories that use agent_workbench. Combine with agent-workbench-toolbox to discover the project, edit firmware, build, flash, validate with UART/diag/monitor, and produce evidence-backed reports without project-specific assumptions.
---

# Agent Workbench Feature

Use this workflow when the user asks to add, modify, or validate firmware behavior: peripherals, CLI commands, protocols, state logic, control loops, status reporting, or "implement and verify" work.

Always pair with `agent-workbench-toolbox`.

## Feature Flow

1. Run `doctor --json`.
2. Run `scan-project --json`.
3. Read existing source and generated headers before choosing hardware parameters.
4. Run `context --mode feature --stage analyze --json` when a compact workbench brief helps.
5. Implement the smallest coherent firmware change.
6. Run `build --json`; use `fix-build --json` only for normal compiler/linker failures.
7. Flash the board when real hardware evidence is needed.
8. Validate with UART/diag commands that prove user-visible behavior.
9. Add or update monitor items in `agent_workbench/agent_workbench.yaml` when internal state, registers, counters, or trends are needed.
10. Run `monitor probe --json` before longer monitor sampling.
11. Run `verify current --json`, then `report --latest --json`; use `compare --latest --json` for regressions.
12. Produce a feature report using [references/feature-report-template.md](references/feature-report-template.md).

## Read When Needed

- Standard feature path: [references/feature-flow.md](references/feature-flow.md)
- Implementation method: [references/feature-development-methodology.md](references/feature-development-methodology.md)
- Acceptance patterns: [references/feature-acceptance-patterns.md](references/feature-acceptance-patterns.md)
- Report template: [references/feature-report-template.md](references/feature-report-template.md)
- Monitor configuration: `agent-workbench-toolbox/references/monitor-configuration.md`

## Completion Standard

A feature is not complete because it builds. It is complete only when the report can show:

- what changed
- why the change matches the current project's hardware and software structure
- build success
- real-board evidence through UART/diag/monitor as appropriate
- stable ready/prompt and command responses when CLI behavior is involved
- monitor samples or register reads when internal/runtime state is part of the claim
- unresolved risks and the exact evidence paths
