---
name: agent-workbench-test
description: Use for STM32 test design, runtime verification, regression probes, assertion planning, real-board validation, and failure triage in repositories that use agent_workbench. Combine with agent-workbench-toolbox to design high-quality tests from source behavior and runtime evidence, then validate them with build, flash, UART, diag, monitor, verify, report, and compare.
---

# Agent Workbench Test

Use this workflow when the user asks for test cases, regression coverage, assertions, verification, failure analysis, or real-board validation.

Always pair with `agent-workbench-toolbox`.

## Test Flow

1. Run `doctor --json` and `scan-project --json`.
2. Identify the behavior contract from source, CLI help/status, user request, existing evidence, and hardware constraints.
3. Build a coverage matrix: happy path, boundary values, invalid input, state transition, reset behavior, persistence if relevant, timing/trend, and regression probes.
4. Choose the evidence surface for each case: UART command, diag exchange, monitor item, build/unit self-check, or report/compare artifact.
5. If monitor evidence is needed, update `agent_workbench/agent_workbench.yaml` automatically and run `monitor probe --json`.
6. Run `build --json`, flash when real-board validation is needed, then execute UART/diag/monitor probes.
7. Run `test run --json` only when the migrated project has a configured host/unit test command.
8. Run `verify current --json`, `report --latest --json`, and `compare --latest --json` when regression comparison matters.
9. Produce a test report using [references/test-report-template.md](references/test-report-template.md).

## Read When Needed

- End-to-end test path: [references/test-flow.md](references/test-flow.md)
- Test design methodology: [references/test-design-methodology.md](references/test-design-methodology.md)
- Coverage matrix: [references/test-coverage-matrix.md](references/test-coverage-matrix.md)
- Assertion patterns: [references/assertion-patterns.md](references/assertion-patterns.md)
- Failure triage: [references/test-failure-triage.md](references/test-failure-triage.md)
- Report template: [references/test-report-template.md](references/test-report-template.md)
- Monitor configuration: `agent-workbench-toolbox/references/monitor-configuration.md`

## Quality Bar

Good STM32 tests are evidence-driven:

- they assert externally visible behavior when possible
- they observe internal state only through deliberate monitor items
- they cover boundaries, invalid inputs, reset/restart, and regression risks
- they avoid brittle strings except stable ready/prompt/help/status text
- they report exactly which evidence proves or fails each case
