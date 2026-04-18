# Agent Workbench

`agent_workbench/` is the automation control plane for this STM32 UART CLI project.

It is not just a loose script bundle. It provides one stable entry point for:

- environment checks
- CMake build
- flash and reset
- UART CLI probing
- monitor capture
- automated debug sessions
- automated feature validation sessions
- report and compare generation
- VS Code task generation

For this repository, the current board-facing defaults are:

- project: `serial`
- build output: `build/cmake-debug/serial.elf`
- UART console: `USART2 / PA2(TX) / PA3(RX) / 115200 8N1`
- diagnostic UART: `USART1 / PA9(TX) / PA10(RX) / 115200 8N1 / Modbus-like RTU`
- ready banner: `STM32 UART CLI ready.`
- prompt: `cli>`

The single source of truth is [agent_workbench.yaml](agent_workbench.yaml).

## Layout

- `agent_workbench.yaml`: project, tools, outputs, UART, prompts, and workflow config
- `bin/`: Windows launchers
- `core/`: Python implementation
- `checks/`: compatibility scripts
- `prompts/`: Continue prompt templates
- `tasks/`: debug and feature task specs
- `generated/`: generated verification assets
- `evidence/`: debug and feature session evidence

## Quick Start

```powershell
cd H:\stm32_RAG\code\serial
agent_workbench\bin\setup.bat
agent_workbench.bat doctor
agent_workbench.bat init-vscode
agent_workbench.bat build
```

`init-vscode` generates:

- `agent_workbench.bat`
- `setup_workbench.bat`
- `.vscode/tasks.json`

## Main Commands

```powershell
agent_workbench.bat doctor
agent_workbench.bat build
agent_workbench.bat flash --method stlink_cli
agent_workbench.bat flash --method openocd_cmd
agent_workbench.bat reset --method stlink_cli
agent_workbench.bat context --mode debug --stage analyze
agent_workbench.bat context --mode feature --stage implement --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat context --mode feature --stage verify --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat context --stage resume
agent_workbench.bat autoflow --goal "Use TIM3 to blink the RED LED at about 1 Hz"
agent_workbench.bat autoflow --resume
agent_workbench.bat decompose --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --command red on --command green on --command blue on --command all off
agent_workbench.bat diag exchange --hex "01 03 00 10 00 03" --append-crc modbus
agent_workbench.bat uart console
agent_workbench.bat test generate --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat test run
agent_workbench.bat session debug
agent_workbench.bat session feature --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat compare --latest
agent_workbench.bat report --session agent_workbench\evidence\sessions\<session_name>
agent_workbench.bat report --latest
agent_workbench.bat verify current --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat init-vscode
```

## Local-Model Workflow

The local-model path now uses staged artifacts instead of one large prompt:

- `*_brief.md`: one-screen summary for the current stage
- `*_facts.json`: evidence-backed facts with stable ids
- `*_constraints.json`: allowed reads, allowed edits, and anti-hallucination rules
- `task_breakdown.md`: small stage-aligned subtasks for the current task
- `task_breakdown.json`: machine-readable breakdown state for tooling
- `*_resume.md`: resume card for the next round
- `*_paste.md`: ready-to-paste Continue prompt
- `agent_state.json`: current mode, stage, profile, latest session, and next commands
- `autoflow_state.json`: one-line task goal, current stage, current subtasks, and stop conditions
- `autoflow_start.md`: the single start card Continue should read after `autoflow --goal ...`

When a task is attached, the workbench now auto-generates a task breakdown so local models can finish one small subtask group at a time. The default stage mapping is:

- `analyze`: understand goal and lock the smallest scope
- `implement`: make the smallest change and pass local checks
- `verify`: run validation and close the loop with evidence

Profiles are configured under `agent.profiles` in [agent_workbench.yaml](agent_workbench.yaml):

- `balanced_local`
- `deepseek16k`
- `qwen32k`

The staged VS Code tasks and `context` flow use `agent.default_profile` by default. You only need `--profile ...` when you want to temporarily override the configured default.

## Board CLI Commands

The current firmware CLI is text-based and command-driven. The standard commands are:

```text
help
help <command>
status
led <red|green|blue|all> <on|off|toggle>
red <on|off|toggle>
green <on|off|toggle>
blue <on|off|toggle>
all <on|off|toggle>
diag_status
```

Typical manual smoke check:

```powershell
agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --command red on --command green on --command blue on --command all off
```

Typical diagnostic-port checks use hex bytes and a Modbus-style CRC:

```powershell
agent_workbench.bat diag exchange --hex "01 03 00 10 00 03" --append-crc modbus
agent_workbench.bat diag exchange --hex "01 06 00 10 00 01" --append-crc modbus
```

`uart exec` is strict by default. It waits for the configured ready banner and prompt, then records:

- `cli_transcript.log`
- `cli_diag.json`

If the CLI handshake fails, `cli_diag.json` classifies the likely reason:

- `rx_zero`
- `parser_no_command`
- `tx_or_host_rx`

## VS Code And Continue

The recommended human and agent workflow is:

1. Run `setup_workbench.bat` once.
2. Open the folder in VS Code.
3. Use `Terminal: Run Task` and the generated staged `Agent Workbench: ...` tasks.
4. If the user request is broad, start with `Agent Workbench: Autoflow From Current Goal`.
5. Switch Continue to `Agent` mode.
6. Open `agent_workbench/runtime/autoflow_start.md`.
7. Paste only the current stage card into Continue.
8. Have Continue complete only the listed `current_subtasks`, then run `Agent Workbench: Autoflow Resume` after each stage switch.
9. Keep every automation action inside `agent_workbench.bat ...` commands instead of ad-hoc shell chains.

For simple existing CLI actions such as `red on`, `green off`, or `status`, `autoflow` now generates a verify-only path and skips code-edit stages. The generated verify card points Continue to the exact `uart exec --command ...` command instead of a generic feature workflow.

The optimized Chinese walkthrough for this staged autoflow is:

- [VS_CODE_CONTINUE_GUIDE_ZH.md](VS_CODE_CONTINUE_GUIDE_ZH.md)

For immediate validation in PowerShell, prefer the one-command path:

```powershell
cmd /c ".\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml"
```

A repo-specific English guide is available at [VS_CODE_CONTINUE_GUIDE.md](VS_CODE_CONTINUE_GUIDE.md).
A repo-specific Chinese guide is available at [VS_CODE_CONTINUE_GUIDE_ZH.md](VS_CODE_CONTINUE_GUIDE_ZH.md).
For migration into another project, read [MIGRATION_GUIDE_ZH.md](MIGRATION_GUIDE_ZH.md).
For a ready-to-paste Chinese Continue prompt, use [prompts/continue_agent_zh.md](prompts/continue_agent_zh.md).
For a direct Chinese startup prompt for Continue Agent, use [prompts/continue_start_zh.md](prompts/continue_start_zh.md).
For a one-line natural-language autoflow prompt, use [prompts/continue_autoflow_zh.md](prompts/continue_autoflow_zh.md).
For the current project's one-command verification prompt, use [prompts/continue_verify_current_zh.md](prompts/continue_verify_current_zh.md).
For low-context local models, read [LOW_CONTEXT_MODELS_GUIDE_ZH.md](LOW_CONTEXT_MODELS_GUIDE_ZH.md) and use [prompts/continue_low_context_zh.md](prompts/continue_low_context_zh.md).

## Evidence-First Workflow

For debug and feature work, conclusions should be based on generated evidence, not only source inspection.

Primary evidence files:

- `cli_transcript.log`
- `cli_diag.json`
- `uart.log`
- `monitor_samples.csv`
- `assertions.jsonl`
- `session_summary.md`
- `feature_summary.md`
- `compare_vs_*.md`

## Notes

- `uart console` still works best with `pyserial` available in the Python environment.
- If `pyserial` is unavailable, the workbench still supports PowerShell fallback for `uart exec`, `uart run`, and session logging.
- If your debug USB-TTL adapter is not on `COM3`, or the diagnostic adapter is not on `COM5`, update `uart.port` and `diag_uart.port` in [agent_workbench.yaml](agent_workbench.yaml) before running hardware sessions.
