# Debug Session Summary

- generated_at: 2026-04-06T10:05:58.394+00:00
- session_dir: `H:\stm32_RAG\code\serial\agent_workbench\evidence\sessions\serial_cli_debug_com3_retry1`

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
[2026-04-06T10:05:48.729+00:00] [uart] start port=COM3 baud=115200 backend=powershell
[2026-04-06T10:05:58.389+00:00] [uart] stop
```

## CLI Tail
```text
[2026-04-06T10:05:40.729+00:00] [cli] reset-first exit=0
[2026-04-06T10:05:41.234+00:00] [cli] start port=COM3 baud=115200 expect_ready=1 reset_first=1 backend=powershell
[2026-04-06T10:05:47.458+00:00] [cli] ready-missing expected=STM32 UART CLI ready.
[2026-04-06T10:05:47.488+00:00] [cli] stop
```

## CLI Diagnostics
- status: error
- summary: CLI diagnostics unavailable
- detail: OpenOCD or DebugCliStats symbol could not be read.

## Manifest Snapshot
```json
{
  "generated_at": "2026-04-06T10:05:37.663+00:00",
  "mode": "debug",
  "project": "serial",
  "project_root": "H:\\stm32_RAG\\code\\serial",
  "config_path": "H:\\stm32_RAG\\code\\serial\\agent_workbench\\agent_workbench.yaml",
  "task": null
}
```
