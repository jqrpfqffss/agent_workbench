# Artifact Map

Use artifacts as the source of truth. Do not summarize a run from memory.

## Highest Priority Evidence

### `session_verdict.json`

- Best for final pass/fail, blocked status, and root-cause hints.
- Read before making a final claim after `session debug` or `session feature`.

### `direct_verify_summary.json` / `direct_verify_summary.md`

- Best for `verify current`.
- Read verdict, steps, assertions, blocked reason, and linked artifacts.

### `cli_diag.json`

- Best for UART/CLI failure classification.
- Read before editing parser, command handlers, UART init, or prompt logic.

### `cli_transcript.log`

- Best for what actually crossed the serial link.
- Use to confirm ready banner, prompt, command echo, command response, and timeout boundaries.

### `monitor_samples.csv` / `monitor_samples.jsonl`

- Best for runtime values, counters, state transitions, register reads, and trends.
- Treat missing samples or stale values as evidence to investigate, not as proof of firmware behavior.

### `compare_delta.json` / `compare_brief.md`

- Best for regression claims between recent sessions.
- Use after a fix to prove the failure improved and no obvious previous evidence regressed.

### `doctor_report.json` / `doctor_report.md`

- Best for environment and configuration blockers.
- Read before source edits when any command fails due to setup, toolchain, port, flash, or monitor availability.

## Common Runtime Outputs

- `build.log`: compiler/linker truth source.
- `flash.log` or OpenOCD logs: flash/reset truth source.
- `session_brief.md`: concise evidence summary for user-facing reporting.
- `session_summary.md`: broader session narrative and artifact links.
- `monitor_snapshot.csv`: latest monitor values for quick inspection.
- `monitor_session.jsonl`: monitor session events and metadata.
- `report.md` or latest report artifact: generated evidence report.

## Reading Order By Situation

- Build failure: command JSON -> `build.log` -> `fix-build` suggestions.
- Flash failure: command JSON -> flash/openocd log -> `doctor_report.json`.
- Ready/prompt missing: UART JSON -> `cli_diag.json` -> `cli_transcript.log` -> reset/flash evidence.
- CLI behavior mismatch: transcript -> `cli_diag.json` -> source handler -> monitor items if internal state is unclear.
- Monitor failure: monitor JSON -> monitor output dir -> `doctor_report.json` -> YAML monitor config -> OpenOCD/debug state.
- Regression: `compare_delta.json` -> previous and latest session summaries -> focused UART/monitor repro.

## Reporting Rule

When reporting to the user, include exact artifact paths and the specific fields or lines that support the conclusion.
