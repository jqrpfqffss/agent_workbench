# Debug Session Summary

- generated_at: 2026-04-06T10:14:59.839+00:00
- session_dir: `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_debug_com3_diag_v2`

## Evidence Files
- session_manifest.json: exists
- commands.log: exists
- doctor_report.md: exists
- uart.log: exists
- cli_transcript.log: exists
- cli_diag.json: exists
- monitor_samples.csv: missing
- assertions.jsonl: missing

## Monitor Stats
- no valid monitor samples

## UART Tail
```text
[2026-04-06T10:14:50.147+00:00] [uart] start port=COM3 baud=115200 backend=powershell
[2026-04-06T10:14:59.833+00:00] [uart] stop
```

## CLI Tail
```text
[2026-04-06T10:14:41.446+00:00] [cli] reset-first exit=0
[2026-04-06T10:14:41.924+00:00] [cli] start port=COM3 baud=115200 expect_ready=1 reset_first=1 backend=powershell
[2026-04-06T10:14:48.144+00:00] [cli] ready-missing expected=STM32 UART CLI ready.
[2026-04-06T10:14:48.175+00:00] [cli] stop
```

## CLI Diagnostics
- status: error
- summary: CLI diagnostics unavailable
- detail: OpenOCD or DebugCliStats symbol could not be read.

## Manifest Snapshot
```json
{
  "generated_at": "2026-04-06T10:14:38.358+00:00",
  "mode": "debug",
  "project": "serial",
  "project_root": "H:\\stm32_RAG\\code\\serial",
  "config_path": "H:\\stm32_RAG\\code\\serial\\agent_workbench\\agent_workbench.yaml",
  "task": null
}
```
