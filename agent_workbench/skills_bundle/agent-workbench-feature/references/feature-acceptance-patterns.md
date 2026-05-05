# Feature Acceptance Patterns

Use these patterns when defining or updating feature acceptance.

## CLI-Visible Features

Prefer:

- `cli_contains` assertions with short stable strings
- explicit ack strings defined by the user-visible behavior contract
- status commands that expose the current value or mode

Avoid:

- vague free-form prose
- multiline outputs that are hard to assert
- changing ready/prompt/help text without a strong reason

## Monitor-Driven Features

When runtime state matters, add:

- a status command for human-readable confirmation when practical
- monitor items for numeric confirmation
- range-based or trend-based expectations when exact values may vary slightly
- a liveness counter or state transition marker

## State And Control Features

Good patterns:

- one control command
- one status command
- one short ack string
- one monitor or transcript check
- one reset or disabled-state check when relevant

## Stable Strings

Keep these stable unless the user explicitly changes the public protocol:

- ready banner
- prompt
- help headings
- status labels
- ack strings used by assertions
