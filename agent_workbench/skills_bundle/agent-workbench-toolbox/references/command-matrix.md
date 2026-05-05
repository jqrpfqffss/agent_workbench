# Command Matrix

Run commands from the repository root. Prefer:

```powershell
.\agent_workbench\bin\agent_workbench.bat <command> --json
```

If OpenCode cannot execute the batch form, use:

```powershell
python ".\agent_workbench\workbench.py" <command> --json
```

Every JSON command commonly exposes `command`, `exit_code`, `status`, `summary`, `details`, `artifacts`, and `timestamp`. Field names can vary by command, so inspect the returned JSON instead of assuming a fixed schema.

## Discovery

### `doctor --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

- Use for environment, toolchain, flash, UART, diag, monitor, and config readiness.
- Read `details.fail_count`, `details.warn_count`, `details.results[]`, `artifacts.report_json`, `artifacts.report_md`.
- If failures exist, stop source edits and report the blockers.

### `scan-project --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat scan-project --json
```

- Use before choosing source files, CLI probes, handles, symbols, monitor candidates, or verification paths.
- Read `details.project`, source roots, CLI command discoveries, UART settings, user code regions, handles, symbols, and monitor candidates.
- If scan is incomplete, inspect the repository directly before making assumptions.

### `context --mode <feature|debug|test> --stage <analyze|implement|verify|resume> --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat context --mode feature --stage analyze --json
```

- Use when OpenCode needs a compact, stage-specific brief.
- Read generated brief/facts/constraints/resume artifacts from `artifacts`.

## Build And Repair

### `build --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat build --json
```

- Use after edits and before hardware validation.
- Read `exit_code`, `summary`, error/warning counts, `errors[]`, `warnings[]`, and `artifacts.log_path`.
- On failure, inspect the first real compiler/linker error and use `fix-build`.

### `fix-build --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat fix-build --json
```

- Use after a normal compile/link failure.
- Read `fixes[]` with file, line, message, and suggested fix fields.
- Keep repairs narrow; rerun `build --json` after each repair.

## Hardware Actions

### `flash --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat flash --json
```

- Use after build success when the claim needs real-board evidence.
- Read method, exit code, and flash/openocd log artifact.
- No user approval is required by the skill layer.

### `reset --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat reset --json
```

- Use when boot, ready banner, prompt, or reset-time behavior matters.
- Follow with UART, diag, or monitor evidence.

## UART And Diag

### `uart exec ... --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json
```

- Use for CLI handshake, prompt, black-box command behavior, and user-visible feature validation.
- Choose commands from scan output, existing help/status commands, changed feature commands, or prior runtime evidence.
- Read `details.saw_ready`, `details.saw_prompt`, command timeouts, transcript artifacts, `cli_diag.json`, and `cli_transcript.log`.
- On failure, classify with `cli_diag.json` before editing source.

### `diag exec ... --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat diag exec --script <requests.txt> --json
```

- Use when the project has a diagnostic UART protocol or CLI is not enough.
- Read exchange count, classification, timeout/error fields, and result/log artifacts.

## Monitor

Before monitor commands, read [monitor-configuration.md](monitor-configuration.md). OpenCode should update `agent_workbench/agent_workbench.yaml` itself when items are missing or stale.

### `monitor probe --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat monitor probe --json
```

- Use for quick readability checks of symbols, memory addresses, and registers.
- Read item results, read errors, and monitor output directory.

### `monitor run --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat monitor run --json
```

- Use for timed samples, trends, state transitions, ranges, and regression evidence.
- Inspect `monitor_samples.csv`, `monitor_samples.jsonl`, snapshots, and session metadata.

### `monitor start/status/stop/export --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat monitor start --json
.\agent_workbench\bin\agent_workbench.bat monitor status --json
.\agent_workbench\bin\agent_workbench.bat monitor stop --json
.\agent_workbench\bin\agent_workbench.bat monitor export --json
```

- Use for longer captures while OpenCode performs UART/diag actions between start and stop.

## Verification And Reports

### `test run --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat test run --json
```

- Use only when the migrated project has a configured host/unit test command.
- Treat these tests as repository self-checks, not a replacement for real-board evidence.

### `verify current --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat verify current --json
```

- Use for the shortest end-to-end verification summary available in the current project.
- Read `direct_verify_summary.json`, `direct_verify_summary.md`, verdict/summary/assertion fields, and referenced runtime artifacts.

### `report --latest --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat report --latest --json
```

- Use to rebuild the latest human-readable evidence summary.
- Read session directory, report path, summary line, and linked artifacts.

### `compare --latest --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat compare --latest --json
```

- Use for regression comparison between recent evidence sessions.
- Read `compare_delta.json` and `compare_brief.md`.

## Session Helpers

### `session debug --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat session debug --json
```

- Use when a debug conversation needs a full evidence bundle.
- Read `session_verdict.json`, `session_brief.md`, and `session_summary.md`.

### `session feature --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat session feature --json
```

- Use when feature validation needs a broader evidence bundle.
- Read the session directory and summary artifacts.
