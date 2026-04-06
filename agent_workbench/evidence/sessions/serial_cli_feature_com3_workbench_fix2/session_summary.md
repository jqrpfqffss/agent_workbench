# Debug Session Summary

- generated_at: 2026-04-06T10:33:02.901+00:00
- session_dir: `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_feature_com3_workbench_fix2`

## Evidence Files
- session_manifest.json: exists
- commands.log: exists
- doctor_report.md: exists
- uart.log: exists
- cli_transcript.log: exists
- cli_diag.json: missing
- monitor_samples.csv: missing
- assertions.jsonl: exists

## Monitor Stats
- no valid monitor samples

## UART Tail
```text
[2026-04-06T10:32:53.182+00:00] [uart] start port=COM3 baud=115200 backend=powershell
[2026-04-06T10:33:02.890+00:00] [uart] stop
```

## CLI Tail
```text
[2026-04-06T10:32:51.895+00:00] < blue on
[2026-04-06T10:32:51.900+00:00] < [ok] blue -> on
[2026-04-06T10:32:51.901+00:00] < System status:
[2026-04-06T10:32:51.902+00:00] <   UART: USART2 @ 115200 8N1
[2026-04-06T10:32:51.903+00:00] <   Pins: TX=PA2, RX=PA3
[2026-04-06T10:32:51.904+00:00] <   LED RED  : on
[2026-04-06T10:32:51.906+00:00] <   LED GREEN: on
[2026-04-06T10:32:51.908+00:00] <   LED BLUE : on
[2026-04-06T10:32:51.909+00:00] < cli>
[2026-04-06T10:32:51.910+00:00] > all off
[2026-04-06T10:32:51.912+00:00] < all off
[2026-04-06T10:32:51.918+00:00] < [ok] all -> off
[2026-04-06T10:32:51.919+00:00] < System status:
[2026-04-06T10:32:51.919+00:00] <   UART: USART2 @ 115200 8N1
[2026-04-06T10:32:51.920+00:00] <   Pins: TX=PA2, RX=PA3
[2026-04-06T10:32:51.922+00:00] <   LED RED  : off
[2026-04-06T10:32:51.924+00:00] <   LED GREEN: off
[2026-04-06T10:32:51.927+00:00] <   LED BLUE : off
[2026-04-06T10:32:51.928+00:00] < cli>
[2026-04-06T10:32:51.928+00:00] > green off
[2026-04-06T10:32:51.931+00:00] < green off
[2026-04-06T10:32:51.937+00:00] < [ok] green -> off
[2026-04-06T10:32:51.937+00:00] < System status:
[2026-04-06T10:32:51.938+00:00] <   UART: USART2 @ 115200 8N1
[2026-04-06T10:32:51.939+00:00] <   Pins: TX=PA2, RX=PA3
[2026-04-06T10:32:51.940+00:00] <   LED RED  : off
[2026-04-06T10:32:51.943+00:00] <   LED GREEN: off
[2026-04-06T10:32:51.945+00:00] <   LED BLUE : off
[2026-04-06T10:32:51.946+00:00] < cli>
[2026-04-06T10:32:51.947+00:00] > blue toggle
[2026-04-06T10:32:51.949+00:00] < blue toggle
[2026-04-06T10:32:51.955+00:00] < [ok] blue -> toggle
[2026-04-06T10:32:51.955+00:00] < System status:
[2026-04-06T10:32:51.958+00:00] <   UART: USART2 @ 115200 8N1
[2026-04-06T10:32:51.958+00:00] <   Pins: TX=PA2, RX=PA3
[2026-04-06T10:32:51.960+00:00] <   LED RED  : off
[2026-04-06T10:32:51.961+00:00] <   LED GREEN: off
[2026-04-06T10:32:51.963+00:00] <   LED BLUE : on
[2026-04-06T10:32:51.964+00:00] < cli>
[2026-04-06T10:32:51.989+00:00] [cli] stop
```

## CLI Diagnostics
- cli_diag.json missing

## Manifest Snapshot
```json
{
  "generated_at": "2026-04-06T10:32:46.207+00:00",
  "mode": "feature",
  "project": "serial",
  "project_root": "H:\\stm32_RAG\\code\\serial",
  "config_path": "H:\\stm32_RAG\\code\\serial\\agent_workbench\\agent_workbench.yaml",
  "task": {
    "id": "cli_automation_regression",
    "mode": "feature",
    "goal": "Keep the USART2 text CLI command-driven, automation-friendly, and safe for repeated debug sessions.",
    "scope": {
      "include": [
        "Core/Src/cli.c",
        "Core/Src/app_cli_commands.c",
        "Core/Src/main.c",
        "Core/Inc",
        "CMakeLists.txt"
      ],
      "exclude": [
        "Drivers"
      ]
    },
    "acceptance": {
      "blackbox": [
        {
          "name": "cli_ready_banner_seen",
          "type": "cli_ready",
          "needle": "STM32 UART CLI ready."
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
          "name": "cli_help_lists_commands",
          "type": "cli_contains",
          "needle": "Available commands:"
        },
        {
          "name": "cli_status_reports_uart",
          "type": "cli_contains",
          "needle": "UART: USART2 @ 115200 8N1"
        },
        {
          "name": "cli_status_reports_led",
          "type": "cli_contains",
          "needle": "LED RED"
        },
        {
          "name": "cli_red_ack",
          "type": "cli_contains",
          "needle": "[ok] red -> on"
        },
        {
          "name": "cli_green_ack",
          "type": "cli_contains",
          "needle": "[ok] green -> off"
        },
        {
          "name": "cli_blue_ack",
          "type": "cli_contains",
          "needle": "[ok] blue -> toggle"
        },
        {
          "name": "cli_all_off_ack",
          "type": "cli_contains",
          "needle": "[ok] all -> off"
        }
      ],
      "unit": [
        "help output documents the command table and usage strings",
        "led command accepts red green blue and all targets",
        "alias commands red green blue and all delegate to the same LED control path",
        "CLI parser tolerates CR LF and backspace without breaking prompt recovery"
      ]
    },
    "observability": {
      "notes": [
        "keep the ready banner and cli> prompt as stable machine-readable markers",
        "prefer explicit command responses over unsolicited serial output",
        "keep control acknowledgements short and easy to assert from cli_transcript.log"
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
        "status",
        "red on",
        "green off",
        "blue toggle",
        "all off"
      ]
    }
  }
}
```
