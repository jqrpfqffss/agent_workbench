# Debug Session Summary

- generated_at: 2026-04-05T04:04:04.156+00:00
- session_dir: `H:\stm32_RAG\code\SmartFarm\agent_workbench\evidence\sessions\cli_regression_host`

## Evidence Files
- session_manifest.json: exists
- commands.log: exists
- doctor_report.md: exists
- uart.log: missing
- cli_transcript.log: missing
- monitor_samples.csv: exists
- assertions.jsonl: exists

## Monitor Stats
- temp_c: count=92 min=27.5429 max=27.5864 last=27.5864
- humidity: count=92 min=82.4744 max=82.7043 last=82.6334
- soil_moisture: count=92 min=48.0000 max=52.0000 last=49.0000
- light_lux: count=92 min=0.0000 max=0.0000 last=0.0000

## UART Tail
- uart log empty or unavailable

## CLI Tail
- cli transcript empty or unavailable

## Manifest Snapshot
```json
{
  "generated_at": "2026-04-05T04:03:45.098+00:00",
  "mode": "feature",
  "project": "SmartFarm",
  "project_root": "H:\\stm32_RAG\\code\\SmartFarm",
  "config_path": "H:\\stm32_RAG\\code\\SmartFarm\\agent_workbench\\agent_workbench.yaml",
  "task": {
    "id": "cli_automation_regression",
    "mode": "feature",
    "goal": "Keep the board UART interface command-driven, automation-friendly, and safe for repeated debug sessions.",
    "scope": {
      "include": [
        "Core/App/cli",
        "Core/App/Tasks/SensorTask.c",
        "Core/App/global",
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
          "name": "cli_help_lists_version",
          "type": "cli_contains",
          "needle": "version | version"
        },
        {
          "name": "cli_version_reports_fw",
          "type": "cli_contains",
          "needle": "version fw="
        },
        {
          "name": "cli_selftest_reports_status",
          "type": "cli_contains",
          "needle": "selftest status="
        },
        {
          "name": "cli_alerts_reports_count",
          "type": "cli_contains",
          "needle": "alerts count="
        }
      ],
      "unit": [
        "help output documents the command and usage table",
        "pump command accepts auto, on, and off",
        "alert buffer can be queried without unsolicited JSON noise"
      ]
    },
    "observability": {
      "notes": [
        "keep CLI responses single-line and parseable where practical",
        "prefer command-driven responses over unsolicited serial output"
      ]
    },
    "verify": {
      "sequence": [
        "doctor",
        "build",
        "test",
        "debug"
      ],
      "cli_commands": [
        "help",
        "version",
        "state",
        "alerts",
        "selftest"
      ]
    }
  }
}
```
