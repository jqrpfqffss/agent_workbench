# Test Flow

## Design

1. Extract the behavior contract from the user request, source, CLI help/status output, hardware limits, and previous evidence.
2. Build a coverage matrix before writing or running probes.
3. Map every case to a concrete evidence surface: UART, diag, monitor, build/unit self-check, verify summary, or compare delta.
4. Define stable assertions: exact strings only for stable protocol text, numeric ranges for measured values, monotonic/trend expectations for counters, and state transitions for control logic.

## Execute

1. `doctor --json`
2. `scan-project --json`
3. `build --json`
4. `flash --json` when real-board behavior matters
5. `uart exec ... --json` and/or `diag exec ... --json`
6. update monitor YAML and run `monitor probe --json` or `monitor run --json` when internal state matters
7. `test run --json` only for configured repository self-tests
8. `verify current --json`
9. `report --latest --json`
10. `compare --latest --json` when regression evidence matters

## Improve

- If a probe is too weak, add a stronger UART/diag assertion or monitor item.
- If evidence is flaky, make the assertion less timing-sensitive or add a readiness/liveness check.
- If source behavior is wrong, fix source and rerun the smallest failing case first.
- If environment blocks evidence, report the blocker instead of claiming test failure.
