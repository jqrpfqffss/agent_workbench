# Portable Migration Example

To move this workbench into another STM32 project:

1. Copy the whole `agent_workbench/` directory.
2. Edit `agent_workbench/agent_workbench.yaml`, including both `uart` and `diag_uart`.
3. Run `agent_workbench\bin\setup.bat`.
4. Run `agent_workbench.bat doctor`.
5. Run `agent_workbench.bat init-vscode`.

For host-side diagnostic UART validation, the portable smoke command is:

```powershell
agent_workbench.bat diag exec
```

In this sample repository, `diag_uart.port` intentionally points at the same `COM3` CLI port so the new host tooling can be validated without changing the firmware. After migration, point `diag_uart.port` at the real protocol UART.

For a full beginner-friendly Chinese migration guide, read:

- `agent_workbench/MIGRATION_GUIDE_ZH.md`
