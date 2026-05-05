# Failure Routing

Classify the failure layer before changing source. Do not jump from the first symptom to a broad rewrite.

## Environment Or Configuration Failure

- Evidence: `doctor --json`, `doctor_report.json/md`.
- Next: report missing tools, paths, ports, OpenOCD, Python, or YAML configuration.
- Avoid: editing firmware source.

## Command Launcher Failure

- Evidence: shell stderr and exit code.
- Next: switch from the batch entry to the direct Python fallback in `opencode-command-execution.md`.
- Avoid: treating launcher failure as a workbench feature failure.

## Build Failure

- Evidence: command JSON, `build.log`, `fix-build --json`.
- Next: repair the first real compiler/linker error with a narrow patch.

## Flash Or Reset Failure

- Evidence: flash/reset JSON, OpenOCD log, `doctor_report.json`.
- Next: check method, probe, target power, paths, and whether the ELF is the current build.

## Ready Missing

- Evidence: UART JSON, `cli_diag.json`, `cli_transcript.log`, reset/flash log.
- Next: separate firmware-not-running, baud/port mismatch, reset timing, and unstable ready string.

## Prompt Missing

- Evidence: transcript and `cli_diag.json`.
- Next: separate parser not entering command loop, prompt string drift, blocked command handling, and UART TX issues.

## Parser Or Command Behavior Failure

- Evidence: `cli_diag.json`, transcript, related CLI handler source.
- Next: reproduce with the smallest CLI probe; add monitor items when internal state is unclear.

## Monitor Missing Data Or Read Failure

- Evidence: monitor JSON, monitor output directory, `doctor_report.json`, `agent_workbench.yaml`.
- Next: check `monitor.enabled`, ELF path, symbol, address, value type, OpenOCD/debug connection, and target run state.

## Assertion Or Regression Failure

- Evidence: `direct_verify_summary.json`, transcript, monitor samples, `compare_delta.json`.
- Next: decide whether the expectation is stale, behavior truly regressed, evidence is insufficient, or the environment is blocked.
