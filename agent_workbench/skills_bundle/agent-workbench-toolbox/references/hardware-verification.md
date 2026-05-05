# Hardware Verification Gate

Real firmware behavior is not proven by build success alone.

## Minimum Loop

1. `doctor --json` confirms the environment.
2. `build --json` succeeds.
3. `flash --json` programs the current firmware to the board.
4. `uart exec ... --json` or `diag exec ... --json` validates externally visible behavior.
5. If internal state, registers, or trends matter, configure monitor items automatically and run `monitor probe --json` or `monitor run --json`.
6. `verify current --json` or `report --latest --json` provides the verdict/summary.

## When Monitor Is Required

- The user asks to prove variables, state machines, counters, registers, memory addresses, control outputs, or trends.
- UART only says "command succeeded" but does not prove internal state changed.
- Debugging must separate command-not-triggered, state-not-updated, output-not-applied, and sampling-chain failures.

## Reporting Requirement

The final report should include evidence paths for build, flash, UART/diag, monitor when used, and verify/report artifacts.
