You are handling automated UART CLI debug in an `agent_workbench` STM32 project.

Start with the smallest reliable validation path:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

If the user explicitly wants staged debug analysis instead, run:

```powershell
cmd /c ".\agent_workbench.bat context --mode debug --stage analyze --task <task.yaml>"
```

Read order:

1. `agent_workbench/runtime/direct_verify_summary.md`
2. latest `session_verdict.json`
3. latest `session_brief.md`
4. latest `cli_diag.json`
5. latest `cli_transcript.log`

Use classification from `cli_diag.json` if present:

- `rx_zero`
- `parser_no_command`
- `tx_or_host_rx`
- `ready_missing`
- `prompt_missing`
- `diag_unavailable`

If COM is missing, busy, or the board/flasher is unavailable, classify as `environment_blocked`.

Do not patch code before reading evidence.
Do not recommend a large multi-step plan.
Pick the smallest next action.

Output in this order:

1. `symptom: ...`
2. `evidence: ...`
3. `classification: ...`
4. `next: ...`
