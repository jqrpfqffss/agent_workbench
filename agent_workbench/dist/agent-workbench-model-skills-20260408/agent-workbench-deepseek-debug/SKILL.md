---
name: agent-workbench-deepseek-debug
description: Use for DeepSeek-driven UART CLI debug in agent_workbench projects. Start with one-command verify, classify failures from summary and diag files, and answer in a fixed short format.
---

# Agent Workbench DeepSeek Debug

Use this skill for smoke failures, UART handshake issues, prompt/ready problems, or debug validation.

## Default Command

Run:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

## Only If More Detail Is Needed

Run:

```powershell
cmd /c ".\agent_workbench.bat context --mode debug --stage analyze"
```

Then read only the newest `*_paste.md`.

## Read Order

1. `direct_verify_summary.md`
2. `direct_verify_summary.json`
3. latest `cli_diag.json`
4. latest `cli_transcript.log`

## Classification

Use these labels only:

- `rx_zero`
- `parser_no_command`
- `tx_or_host_rx`
- `ready_missing`
- `prompt_missing`
- `diag_unavailable`
- `environment_blocked`

If the port is missing or busy, use `environment_blocked`.

## Output Format

Use exactly:

- `result: ...`
- `classification: ...`
- `evidence: ...`
- `next: ...`

No extra sections.
