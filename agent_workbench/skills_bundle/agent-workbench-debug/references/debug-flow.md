# Debug Flow

## Quick Path

1. Reproduce with the smallest failing command.
2. Run `verify current --json` when available.
3. Read `direct_verify_summary.json`, `cli_diag.json`, `cli_transcript.log`, and monitor artifacts referenced by the run.
4. Classify the layer before editing.

## Explicit Path

1. `doctor --json`
2. `build --json`
3. `flash --json` if the board image may be stale
4. `uart exec ... --json` for CLI-visible symptoms
5. `diag exec ... --json` for diagnostic protocol symptoms
6. update monitor YAML and run `monitor probe --json` for runtime state
7. `session debug --json`
8. `report --latest --json`
9. `compare --latest --json`

## Stop Conditions

- Environment blocker: report exact doctor failure and do not edit source.
- Hardware blocker: report flash/reset/debug connection evidence.
- Unknown command launcher failure: retry with direct Python fallback once, then report if still blocked.
- Evidence conflict: design one narrower probe instead of guessing.
