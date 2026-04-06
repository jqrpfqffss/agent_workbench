# Debug Session Summary

- generated_at: 2026-04-06T10:06:24.624+00:00
- session_dir: `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_feature_com3_retry1`

## Evidence Files
- session_manifest.json: exists
- commands.log: exists
- doctor_report.md: exists
- uart.log: exists
- cli_transcript.log: exists
- cli_diag.json: exists
- monitor_samples.csv: missing
- assertions.jsonl: exists

## Monitor Stats
- no valid monitor samples

## UART Tail
```text
[2026-04-06T10:06:14.961+00:00] [uart] start port=COM3 baud=115200 backend=powershell
[2026-04-06T10:06:24.613+00:00] [uart] stop
```

## CLI Tail
```text
[2026-04-06T10:06:07.023+00:00] [cli] reset-first exit=0
[2026-04-06T10:06:07.516+00:00] [cli] start port=COM3 baud=115200 expect_ready=1 reset_first=1 backend=powershell
[2026-04-06T10:06:13.701+00:00] [cli] ready-missing expected=STM32 UART CLI ready.
[2026-04-06T10:06:13.731+00:00] [cli] stop
```

## CLI Diagnostics
- status: error
- summary: CLI diagnostics unavailable
- detail: OpenOCD or DebugCliStats symbol could not be read.

## Manifest Snapshot
```json
{
  "generated_at": "2026-04-06T10:06:03.924+00:00",
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
