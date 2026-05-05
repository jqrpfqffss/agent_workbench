# Test Report Template

## Summary

- Target behavior: `<what was tested>`
- Result: `<pass/fail/blocked>`
- Validation mode: `<UART / diag / monitor / build self-check / mixed>`
- Board/firmware: `<board, build artifact, flash result>`

## Coverage

| Case | Purpose | Evidence surface | Assertion | Result |
|---|---|---|---|---|
| `<case>` | `<why it matters>` | `<UART/diag/monitor/etc>` | `<expected>` | `<pass/fail/blocked>` |

Include happy path, boundary, invalid input, state transition, reset/restart, timing/trend, and regression cases as relevant.

## Evidence

- Build: `<build JSON/log path>`
- Flash/reset: `<flash/reset artifact path>`
- UART transcript: `<cli_transcript.log path>`
- Diag result: `<diag artifact path>`
- Monitor samples: `<monitor_samples path>`
- Verify summary: `<direct_verify_summary path>`
- Report/compare: `<report/compare artifact path>`

## Failure Analysis

- Failed layer: `<environment/build/flash/UART/diag/monitor/source behavior/assertion>`
- Evidence supporting the classification: `<artifact + field/line>`
- Next smallest action: `<probe or fix>`

## Residual Risk

- `<untested edge or hardware condition>`
- `<flaky evidence or environment dependency>`
