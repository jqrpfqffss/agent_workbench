# Unit Test Plan

- task_id: `cli_automation_regression`
- goal: Keep the USART2 text CLI command-driven, automation-friendly, and safe for repeated debug sessions.

## Unit Acceptance
- help output documents the command table and usage strings
- led command accepts red green blue and all targets
- alias commands red green blue and all delegate to the same LED control path
- CLI parser tolerates CR LF and backspace without breaking prompt recovery