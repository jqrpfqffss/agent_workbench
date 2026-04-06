# Unit Test Plan

- task_id: `add_version_cli`
- goal: Add a board CLI command that reports firmware version and build profile.

## Unit Acceptance
- version string is returned in one line
- command handler rejects unexpected extra args