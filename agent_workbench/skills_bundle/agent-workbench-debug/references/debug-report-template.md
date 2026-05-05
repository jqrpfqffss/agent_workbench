# Debug Report Template

Use this template after automated debug or root-cause analysis.

## Required Report Shape

```markdown
**Debug Result**
<root cause found | likely cause | blocked | unresolved> - <one sentence>

**Symptom**
- <what the user or automation observed>

**Failure Layer**
- <environment | build | flash/boot | UART handshake | CLI parser | feature behavior | observability | regression>

**Evidence Chain**
- doctor: <artifact path and relevant result>
- build: <artifact path and relevant result>
- runtime probe: <uart/diag/monitor artifact path and relevant result>
- verdict/report: <session_verdict, session_brief, or direct summary path>
- compare: <compare artifact or "not used">

**Hypotheses Considered**
- <hypothesis> - <accepted/rejected/inconclusive> - <evidence>
- <hypothesis> - <accepted/rejected/inconclusive> - <evidence>

**Most Likely Cause**
<specific cause or blocker, with confidence level>

**Action Taken**
- <code change, probe/config change, or no change>
- <commands rerun after change>

**Remaining Risk**
- <unverified hardware, missing monitor item, flaky evidence path, or none>

**Next Experiment**
<single smallest next probe if unresolved>
```

## Rules

- Separate evidence from speculation.
- State when source edits are not justified yet.
- If blocked by hardware, report the exact blocker and do not invent a firmware cause.
- If root cause is likely but not proven, label it as likely and name the missing proof.
