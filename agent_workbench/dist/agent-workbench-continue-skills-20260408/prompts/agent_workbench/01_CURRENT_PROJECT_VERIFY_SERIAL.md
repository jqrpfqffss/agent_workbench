You are validating the current STM32 serial CLI project only.
Do not modify code, config, docs, tasks, or tests.

Use only PowerShell-safe commands.
Do not use `cd ... && ...`.
Do not use bare `.bat` commands.
Do not build your own long command chain.

Run exactly this from the workspace root:

```powershell
cmd /c ".\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml"
```

After the command completes, read only these files first:

- `agent_workbench/runtime/direct_verify_summary.md`
- `agent_workbench/runtime/direct_verify_summary.json`

If the summary references a feature session directory, then read only the evidence files inside that latest session:

- `session_verdict.json`
- `session_brief.md`
- `session_summary.md`
- `feature_summary.md`
- `assertions.jsonl`
- `cli_transcript.log`
- `cli_diag.json`
- `compare_brief.md`
- `compare_vs_*.md`

Rules:

1. Evidence first, no guessing.
2. If COM, board, or flasher is unavailable, report `environment blocked`.
3. If `cli_diag.json` contains a classification, use it.
4. Do not suggest code changes unless evidence clearly points to source behavior.

Output exactly these four items:

- `result: pass / fail / environment blocked`
- `evidence: key files and key findings`
- `layer: doctor / build / test_run / uart_smoke / feature_session`
- `next: one smallest next action`
