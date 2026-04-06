# Debug Session Summary

- generated_at: 2026-04-04T07:39:49.351+00:00
- session_dir: `H:\stm32_RAG\code\SmartFarm\agent_workbench\evidence\sessions\feature_validation_v2`

## Evidence Files
- session_manifest.json: exists
- commands.log: exists
- doctor_report.md: exists
- uart.log: missing
- monitor_samples.csv: exists
- assertions.jsonl: exists

## Monitor Stats
- temp_c: count=92 min=-65639676338548827488256.0000 max=-65639676338548827488256.0000 last=-65639676338548827488256.0000
- humidity: count=92 min=-0.0000 max=-0.0000 last=-0.0000
- soil_moisture: count=92 min=58090.0000 max=58090.0000 last=58090.0000
- light_lux: count=92 min=56665.0000 max=56665.0000 last=56665.0000

## UART Tail
- uart log empty or unavailable

## Manifest Snapshot
```json
{
  "generated_at": "2026-04-04T07:39:37.163+00:00",
  "mode": "feature",
  "project": "SmartFarm",
  "project_root": "H:\\stm32_RAG\\code\\SmartFarm",
  "config_path": "H:\\stm32_RAG\\code\\SmartFarm\\agent_workbench\\agent_workbench.yaml",
  "task": {
    "id": "add_version_cli",
    "mode": "feature",
    "goal": "Add a board CLI command that reports firmware version and build profile.",
    "scope": {
      "include": [
        "Core/App/cli",
        "Core/App/Tasks",
        "CMakeLists.txt"
      ],
      "exclude": [
        "Drivers",
        "Middlewares"
      ]
    },
    "acceptance": {
      "blackbox": [
        {
          "name": "version_command_report_exists",
          "type": "file_exists",
          "path": "session_manifest.json"
        },
        {
          "name": "version_uart_contains",
          "type": "uart_contains",
          "needle": "version"
        }
      ],
      "unit": [
        "version string is returned in one line",
        "command handler rejects unexpected extra args"
      ]
    },
    "observability": {
      "notes": [
        "update local UART help rows when the command list changes"
      ]
    },
    "verify": {
      "sequence": [
        "doctor",
        "build",
        "test",
        "debug"
      ]
    }
  }
}
```
