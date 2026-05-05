# Assertion Patterns

Use these patterns when writing or refining runtime-verifiable acceptance.

## Preferred CLI Assertions

- `cli_contains`
- `cli_not_contains`
- `cli_ready`
- `cli_prompt_seen`
- `cli_no_timeout`

Use short strings sourced from the current project, runtime evidence, or an explicit behavior contract.

## Preferred Monitor Assertions

Use monitor assertions when runtime state matters:

- last value in range
- counter increased
- state changed after a command
- register bit changed or stayed stable
- trend moved in the expected direction

Choose ranges when exact values may vary slightly.

## CLI Diagnostic Assertions

Use diagnostic JSON fields when available:

- command count
- timeout count
- receive byte count
- parser error count

Avoid using fields not produced by the current project.

## Stable String Guidance

Preserve these unless the user explicitly changes the public protocol:

- ready banner
- prompt
- command table headings
- status labels
- short ack strings

Source these strings from config, doctor output, current CLI transcript, or the explicit user request.

## Bad Patterns

- long prose output as an assertion target
- unstable timestamps in asserted strings
- ambiguous success text that changes often
- exact numeric assertions for values that naturally jitter

## Review Checklist

- every assertion maps to one behavior or one evidence requirement
- every string comes from config, current CLI output, runtime evidence, or the explicit behavior contract
- at least one assertion checks the requested new or changed behavior
- regression work keeps at least one existing command or stable marker
- hardware-dependent behavior includes CLI, diag, or monitor evidence from real-board execution
