# VS Code + Continue Agent Workflow

## 1. Purpose

This guide explains how to use VS Code together with Continue `Agent` mode and `agent_workbench` for:

- automated debug
- automated test generation and execution
- automated feature validation
- evidence-driven reporting

The rule of thumb is simple:

- use `agent_workbench.bat ...` as the stable automation API
- read evidence first
- modify code second
- re-run validation after every change

## 2. One-Time Setup

Open the project root in a terminal:

```powershell
cd H:\stm32_RAG\code\serial
```

Run setup:

```powershell
agent_workbench\bin\setup.bat
```

Then run:

```powershell
agent_workbench.bat doctor
agent_workbench.bat init-vscode
```

This gives you:

- project-level launcher: `agent_workbench.bat`
- project-level setup wrapper: `setup_workbench.bat`
- VS Code task file: `.vscode/tasks.json`

## 3. Current Project Defaults

The workbench is currently configured for this repository as:

- build dir: `build/cmake-debug`
- ELF: `build/cmake-debug/serial.elf`
- UART: `USART2`, `PA2/PA3`, `115200 8N1`
- ready banner: `STM32 UART CLI ready.`
- prompt: `cli>`
- default probe commands:
  - `help`
  - `status`
  - `red on`
  - `green on`
  - `blue on`
  - `all off`

If your USB-TTL port is not `COM3`, edit `agent_workbench/agent_workbench.yaml`.

## 4. VS Code Tasks

After `init-vscode`, use `Terminal: Run Task` and choose:

- `Agent Workbench: Setup`
- `Agent Workbench: Doctor`
- `Agent Workbench: Build`
- `Agent Workbench: Flash (ST-Link)`
- `Agent Workbench: Flash (OpenOCD)`
- `Agent Workbench: UART CLI Smoke`
- `Agent Workbench: Test Generate (Example)`
- `Agent Workbench: Test Generate (CLI Regression)`
- `Agent Workbench: Test Run`
- `Agent Workbench: Debug Session`
- `Agent Workbench: Feature Session (Example)`
- `Agent Workbench: Feature Session (CLI Regression)`
- `Agent Workbench: Compare Latest`

Recommended order:

1. `Agent Workbench: Doctor`
2. `Agent Workbench: Build`
3. `Agent Workbench: UART CLI Smoke` or `Agent Workbench: Debug Session`
4. `Agent Workbench: Compare Latest`

For feature work:

1. `Agent Workbench: Test Generate (CLI Regression)`
2. implement with Continue Agent
3. `Agent Workbench: Test Run`
4. `Agent Workbench: Feature Session (CLI Regression)`
5. `Agent Workbench: Compare Latest`

## 5. Continue Agent Mode

In VS Code:

1. Open Continue.
2. Switch to `Agent` mode.
3. Start your request by telling Continue to read the workbench context first.

Recommended starter prompt for debug:

```text
Read:
- agent_workbench/agent_workbench.yaml
- agent_workbench/prompts/continue_debug.md
- the latest session under agent_workbench/evidence/sessions/
- cli_transcript.log and cli_diag.json if present

Then run:
- agent_workbench.bat doctor
- agent_workbench.bat build
- agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --command red on --command green on --command blue on --command all off

Summarize the symptom, evidence chain, likely root cause, smallest safe change, and validation result.
```

If you want a ready-made Chinese prompt instead of composing your own, paste the content from `agent_workbench/prompts/continue_agent_zh.md`.

Recommended starter prompt for feature work:

```text
Read:
- agent_workbench/agent_workbench.yaml
- agent_workbench/prompts/continue_feature.md
- agent_workbench/tasks/cli_automation_regression.yaml
- agent_workbench/generated/tasks/cli_automation_regression/
- the latest session under agent_workbench/evidence/sessions/

Then run:
- agent_workbench.bat test generate --task agent_workbench/tasks/cli_automation_regression.yaml
- agent_workbench.bat test run

Implement only the smallest required change and validate through the workbench.
```

## 6. Evidence Files To Read First

When Continue or a human reviews a result, read these first:

- `agent_workbench/evidence/sessions/<session>/cli_transcript.log`
- `agent_workbench/evidence/sessions/<session>/cli_diag.json`
- `agent_workbench/evidence/sessions/<session>/uart.log`
- `agent_workbench/evidence/sessions/<session>/assertions.jsonl`
- `agent_workbench/evidence/sessions/<session>/session_summary.md`
- `agent_workbench/evidence/sessions/<session>/feature_summary.md`
- `agent_workbench/evidence/sessions/<session>/compare_vs_*.md`

If CLI handshake fails, classify by `cli_diag.json` first:

- `rx_zero`: likely COM port, wiring, or wrong UART path
- `parser_no_command`: board received bytes but command parsing/execution failed
- `tx_or_host_rx`: board executed, but the host did not capture the response correctly

## 7. Automated Debug Loop

Use this sequence:

```powershell
agent_workbench.bat doctor
agent_workbench.bat build
agent_workbench.bat flash
agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --command red on --command green on --command blue on --command all off
agent_workbench.bat session debug
agent_workbench.bat compare --latest
```

Expected outputs:

- `doctor_report.md`
- `cli_transcript.log`
- `cli_diag.json`
- `session_summary.md`
- `compare_vs_*.md`

## 8. Automated Test Workflow

Generate test assets:

```powershell
agent_workbench.bat test generate --task agent_workbench\tasks\cli_automation_regression.yaml
```

Run host-side workbench tests:

```powershell
agent_workbench.bat test run
```

Generated outputs go under:

- `agent_workbench/generated/tasks/<task_id>/blackbox_assertions.yaml`
- `agent_workbench/generated/tasks/<task_id>/unit_test_plan.md`
- `agent_workbench/generated/tasks/<task_id>/*_host_test_skeleton.c`

## 9. Automated Feature Validation

For a real feature loop:

```powershell
agent_workbench.bat test generate --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat test run
agent_workbench.bat session feature --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat compare --latest
```

Read:

- `feature_summary.md`
- `session_summary.md`
- `assertions.jsonl`
- `compare_vs_*.md`

## 10. Missing Piece Checklist

If something does not work, check these first:

- wrong COM port in `agent_workbench.yaml`
- wrong UART baud rate in `agent_workbench.yaml`
- stale toolchain file path
- missing `.vscode/tasks.json` because `init-vscode` was not run
- missing `pyserial` for interactive `uart console`
- no board connected during `flash` / `session debug` / `session feature`

For this repository, the workbench config and task files have already been aligned to the current `serial` project. The remaining environment-specific field you may still need to edit is usually `uart.port`.
