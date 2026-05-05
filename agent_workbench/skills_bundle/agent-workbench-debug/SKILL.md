---
name: agent-workbench-debug
description: Use for STM32 automated debugging in repositories that use agent_workbench: UART failures, prompt or ready issues, flash/reset problems, runtime regressions, monitor read failures, assertion failures, or root-cause analysis. Combine with agent-workbench-toolbox and follow evidence-first triage before editing source.
---

# Agent Workbench Debug

Use this workflow when the user asks to debug, diagnose, find root cause, explain a failure, or recover a broken STM32 automation run.

Always pair with `agent-workbench-toolbox`.

## Debug Flow

1. Reproduce once with the smallest command that shows the problem.
2. Run `doctor --json` and read the latest evidence artifacts.
3. If build is involved, run `build --json` and only then `fix-build --json` when appropriate.
4. If UART/CLI is involved, run `uart exec ... --json`, then inspect `cli_diag.json` and `cli_transcript.log`.
5. If diag protocol is involved, run `diag exec ... --json`.
6. If runtime state is unclear, add or adjust monitor items in `agent_workbench/agent_workbench.yaml`, then run `monitor probe --json`.
7. Use `session debug --json`, `report --latest --json`, and `compare --latest --json` when the failure needs a fuller evidence bundle.
8. Rank root causes from evidence before changing source.
9. After a fix, rerun the minimal failing probe and one broader regression probe.
10. Produce a debug report using [references/debug-report-template.md](references/debug-report-template.md).

## Read When Needed

- Debug paths: [references/debug-flow.md](references/debug-flow.md)
- Debug methodology: [references/debug-methodology.md](references/debug-methodology.md)
- Experiment playbook: [references/debug-experiment-playbook.md](references/debug-experiment-playbook.md)
- Command playbook: [references/debug-command-playbook.md](references/debug-command-playbook.md)
- Diag classifications: [references/diag-codes.md](references/diag-codes.md)
- Evidence-first root cause: [references/evidence-first-root-cause.md](references/evidence-first-root-cause.md)
- Report template: [references/debug-report-template.md](references/debug-report-template.md)
- Monitor configuration: `agent-workbench-toolbox/references/monitor-configuration.md`

## Rule

Do not start by editing code unless the evidence already isolates a source-level cause. Debugging must narrow the failure layer first: launcher, environment, flash/reset, UART RX/TX, parser, CLI behavior, monitor/debug access, firmware logic, or regression.
