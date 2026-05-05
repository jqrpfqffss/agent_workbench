# Test Coverage Matrix

Use this matrix to decide whether a validation plan is strong enough for a requested behavior.

## Matrix Columns

Each important behavior should map to:

- behavior
- stimulus
- expected evidence
- assertion type
- evidence source
- failure layer
- hardware required
- regression relevance

## Matrix Template

```markdown
| Behavior | Stimulus | Expected Evidence | Assertion | Source | Failure Layer | HW Required | Regression |
|---|---|---|---|---|---|---|---|
| <behavior> | <CLI/diag/event> | <ack/status/value> | <assertion type> | <artifact> | <layer> | <yes/no> | <yes/no> |
```

## Minimum Coverage By Work Type

### CLI Command

Required:

- command appears in help or command list
- nominal command returns stable response
- invalid or missing argument recovers prompt when applicable
- existing core commands still work when shared parser code changed

Recommended:

- status command confirms state change
- no timeout assertion

### Peripheral Feature

Required:

- build passes
- initialization path is exercised
- control or trigger path is exercised
- runtime state is visible through CLI, diag, or monitor
- hardware verification is run or explicitly blocked

Recommended:

- boundary values
- disabled or reset state
- regression command for shared subsystem

### Debug Regression

Required:

- failing symptom is reproduced or marked unreproducible
- baseline or previous evidence is compared when available
- failure layer is identified
- next smallest experiment is recorded

### Protocol Or Diag

Required:

- request format is project-defined
- response shape is asserted
- timeout or malformed-response behavior is captured when applicable

## Quality Gates

A validation plan is weak if:

- it only checks build success
- it only checks `help` without the requested behavior
- it asserts strings that do not come from config, runtime evidence, or an explicit behavior contract
- it cannot distinguish environment failure from source behavior failure
- hardware-dependent behavior has no CLI, diag, or monitor evidence path

A validation plan is strong if:

- every key behavior has at least one evidence source
- assertions are diagnostic and single-purpose
- real hardware requirements are explicit
- regression risk is represented when shared code changes
- report artifacts are named in the final report
