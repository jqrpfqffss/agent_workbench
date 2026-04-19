---
name: agent-workbench-debug
description: Use for UART CLI debug, smoke checks, handshake failures, and evidence-first root-cause analysis in STM32 projects that use agent_workbench.
---

# Agent Workbench Debug

Use this skill when the user wants automated debug for UART CLI behavior, serial handshake problems, smoke validation, or root-cause analysis.

## Preferred Start

If the user wants the current status quickly, run:

```powershell
cmd /c ".\agent_workbench.bat verify current --task <task.yaml>"
```

This is the default because it reduces shell mistakes and produces one compact summary file.

If the user explicitly wants a staged debug round instead, run:

```powershell
cmd /c ".\agent_workbench.bat context --mode debug --stage analyze"
```

Then read only the newest `*_paste.md`.

## Focused Debug Loop

When you need the explicit debug path, use:

```powershell
cmd /c ".\agent_workbench.bat doctor"
cmd /c ".\agent_workbench.bat build"
cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status"
cmd /c ".\agent_workbench.bat session debug"
cmd /c ".\agent_workbench.bat compare --latest"
cmd /c ".\agent_workbench.bat report --latest"
```

Do not add extra UART commands unless they are required by the task.

## Read These First

- `agent_workbench/runtime/direct_verify_summary.md`
- latest `session_verdict.json`
- latest `session_brief.md`
- latest `cli_transcript.log`
- latest `cli_diag.json`

## Classification Rules

If `cli_diag.json` exists, classify in this order:

- `rx_zero`: likely wrong COM port, wrong UART path, or no bytes reaching the target
- `parser_no_command`: bytes arrived, parser or command dispatch failed
- `tx_or_host_rx`: command likely ran, but host did not capture the response correctly
- `ready_missing`: board did not show the configured ready banner
- `prompt_missing`: board did not show the configured prompt
- `diag_unavailable`: diagnostic backend could not read `DebugCliStats`; do not over-claim root cause

## Guardrails

- Do not patch code before reading evidence.
- If the summary says `blocked`, treat it as an environment block unless newer evidence disproves that.
- If the board is not connected or the port is missing, say so directly.
- Prefer the smallest next action, not a long speculative plan.

## Default Output

Respond in this order:

1. Symptom
2. Evidence chain
3. Root cause ranking
4. Smallest next action
