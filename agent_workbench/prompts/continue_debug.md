# Continue Debug Prompt

Read `agent_workbench/agent_workbench.yaml` and the latest debug session under `agent_workbench/evidence/sessions/`.
Use `cli_transcript.log` and `cli_diag.json` when present in addition to `uart.log` and monitor outputs.

Your job:

1. Summarize the symptom and the strongest evidence.
2. Identify the most likely root cause.
3. Propose the smallest safe code change.
4. Validate through the stable CLI in this order: `flash`, `uart exec --reset-first --expect-ready`, `session debug`, `compare --latest`.
5. If the CLI handshake fails, use `cli_diag.json` to distinguish `rx_zero`, parser issues, and host receive issues before changing code.
6. Produce a final report with symptom, evidence chain, root cause, code changes, and validation result.
