# Feature Completion Report Template

Use this template for final reports after automated feature development or feature validation.

## Required Report Shape

```markdown
**Feature Result**
<pass | fail | blocked | partial> - <one sentence outcome>

**What Changed**
- <files or modules changed, or "no source changes">
- <runtime probes, CLI commands, or observability paths used>

**Validation Evidence**
- doctor: <pass/fail/block> - <artifact path>
- build: <pass/fail> - <log or JSON artifact path>
- hardware: <pass/fail/skipped/blocked> - <flash/UART/diag/monitor evidence>
- runtime validation: <pass/fail/skipped/blocked> - <UART/diag/monitor/verify evidence>
- report: <session or direct verify summary path>

**Behavior Verified**
- <control command, diag request, or trigger used>
- <expected response, state, monitor value, or assertion result>

**Regression Check**
- <existing behavior checked>
- <compare result or reason compare was not applicable>

**Open Risks**
- <remaining blocker, unverified hardware dependency, or none>

**Next Step**
<single concrete next action if not fully pass>
```

## Rules

- Cite concrete artifact paths.
- Do not say "verified on hardware" unless flash/reset and runtime evidence actually happened.
- If hardware was not run, say `skipped` or `blocked` and explain why.
- If runtime coverage is weak, say what evidence is missing.
- Keep the result aligned with `session_verdict.json`, `direct_verify_summary.json`, or the command JSON payload.
