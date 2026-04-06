# Unit Test Plan

- task_id: `cli_hardware_smoke`
- goal: Verify the USART3 PB10/PB11 CLI handshake, prompt, command execution, and diagnostics on real hardware.

## Unit Acceptance
- CLI handshake emits cli ready and cli> after reset
- ping/help/version/state/alerts/selftest/stats are parseable