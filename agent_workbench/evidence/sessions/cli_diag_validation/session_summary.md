# Debug Session Summary

- generated_at: 2026-04-05T05:27:25.271+00:00
- session_dir: `H:\stm32_RAG\code\SmartFarm\agent_workbench\evidence\sessions\cli_diag_validation`

## Evidence Files
- session_manifest.json: exists
- commands.log: exists
- doctor_report.md: exists
- uart.log: exists
- cli_transcript.log: exists
- cli_diag.json: exists
- monitor_samples.csv: exists
- assertions.jsonl: missing

## Monitor Stats
- temp_c: count=92 min=27.6770 max=27.7060 last=27.6917
- humidity: count=92 min=82.4891 max=82.6444 last=82.5210
- soil_moisture: count=92 min=48.0000 max=51.0000 last=50.0000
- light_lux: count=92 min=0.0000 max=0.0000 last=0.0000

## UART Tail
```text
﻿[2026-04-05T05:27:15.535+00:00] [uart] start port=COM3 baud=9600 backend=powershell
[2026-04-05T05:27:25.241+00:00] [uart] stop
```

## CLI Tail
```text
﻿[2026-04-05T05:27:07.325+00:00] [cli] start port=COM3 baud=9600 expect_ready=1 reset_first=0 backend=powershell
[2026-04-05T05:27:13.494+00:00] [cli] ready-missing expected=cli ready
[2026-04-05T05:27:13.526+00:00] [cli] stop
```

## CLI Diagnostics
- status: ok
- summary: Board did not receive UART bytes
- detail: Check COM port mapping, RX/TX wiring, and whether USART3 PB10/PB11 is the active CLI path.
- stats: rx_bytes=0 rx_lines=0 cmd_ok=0 cmd_err=0 rx_overflow=0 uart_error=0 last_cmd=

## Manifest Snapshot
```json
{
  "generated_at": "2026-04-05T05:26:59.340+00:00",
  "mode": "debug",
  "project": "SmartFarm",
  "project_root": "H:\\stm32_RAG\\code\\SmartFarm",
  "config_path": "H:\\stm32_RAG\\code\\SmartFarm\\agent_workbench\\agent_workbench.yaml",
  "task": null
}
```
