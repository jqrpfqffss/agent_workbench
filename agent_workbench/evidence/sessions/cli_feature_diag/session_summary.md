# Debug Session Summary

- generated_at: 2026-04-05T05:32:21.575+00:00
- session_dir: `H:\stm32_RAG\code\SmartFarm\agent_workbench\evidence\sessions\cli_feature_diag`

## Evidence Files
- session_manifest.json: exists
- commands.log: exists
- doctor_report.md: exists
- uart.log: exists
- cli_transcript.log: exists
- cli_diag.json: exists
- monitor_samples.csv: exists
- assertions.jsonl: exists

## Monitor Stats
- temp_c: count=92 min=27.7834 max=27.8242 last=27.8210
- humidity: count=92 min=81.0402 max=81.1970 last=81.1557
- soil_moisture: count=92 min=48.0000 max=52.0000 last=51.0000
- light_lux: count=92 min=0.0000 max=0.0000 last=0.0000

## UART Tail
```text
[2026-04-05T05:32:11.844+00:00] [uart] start port=COM3 baud=9600 backend=powershell
[2026-04-05T05:32:21.563+00:00] [uart] stop
```

## CLI Tail
```text
[2026-04-05T05:32:03.109+00:00] [cli] reset-first exit=0
[2026-04-05T05:32:03.586+00:00] [cli] start port=COM3 baud=9600 expect_ready=1 reset_first=1 backend=powershell
[2026-04-05T05:32:09.791+00:00] [cli] ready-missing expected=cli ready
[2026-04-05T05:32:09.821+00:00] [cli] stop
```

## CLI Diagnostics
- status: ok
- summary: Board did not receive UART bytes
- detail: Check COM port mapping, RX/TX wiring, and whether USART3 PB10/PB11 is the active CLI path.
- stats: rx_bytes=0 rx_lines=0 cmd_ok=0 cmd_err=0 rx_overflow=0 uart_error=0 last_cmd=

## Manifest Snapshot
```json
{
  "generated_at": "2026-04-05T05:31:55.586+00:00",
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
          "name": "cli_ready_banner_seen",
          "type": "cli_ready"
        },
        {
          "name": "cli_prompt_seen",
          "type": "cli_prompt_seen"
        },
        {
          "name": "cli_has_no_timeout",
          "type": "cli_no_timeout"
        },
        {
          "name": "cli_help_lists_version",
          "type": "cli_contains",
          "needle": "version | version"
        },
        {
          "name": "cli_ping_pong",
          "type": "cli_contains",
          "needle": "pong"
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
        },
        {
          "name": "cli_stats_rx_bytes_non_negative",
          "type": "cli_diag_field_between",
          "field": "stats.rx_bytes",
          "min": 0,
          "max": 1000000
        }
      ],
      "unit": [
        "help output documents the command and usage table",
        "pump command accepts auto, on, and off",
        "alert buffer can be queried without unsolicited JSON noise",
        "stats reports rx/cmd counters and last_cmd"
      ]
    },
    "observability": {
      "notes": [
        "keep CLI responses single-line and parseable where practical",
        "prefer command-driven responses over unsolicited serial output",
        "keep cli ready and cli> as stable machine-readable markers"
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
        "ping",
        "help",
        "version",
        "state",
        "alerts",
        "selftest",
        "stats"
      ]
    }
  }
}
```
