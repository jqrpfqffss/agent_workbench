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
agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --command red on --command green on --command blue on --command all off
agent_workbench.bat uart console
agent_workbench.bat test generate --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat test run
agent_workbench.bat session debug
agent_workbench.bat session feature --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat compare --latest
agent_workbench.bat report --session agent_workbench\evidence\sessions\<session_name>
agent_workbench.bat init-vscode
```

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
```

Typical manual smoke check:

```powershell
agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --command red on --command green on --command blue on --command all off
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
3. Use `Terminal: Run Task` and the generated `Agent Workbench: ...` tasks.
4. Switch Continue to `Agent` mode.
5. Ask Continue to read:
   - `agent_workbench/agent_workbench.yaml`
   - `agent_workbench/prompts/continue_debug.md` or `continue_feature.md`
   - the selected task file under `agent_workbench/tasks/`
   - the latest session under `agent_workbench/evidence/sessions/`
6. Have Continue drive actions through `agent_workbench.bat ...`, not ad-hoc shell command chains.

A repo-specific English guide is available at [VS_CODE_CONTINUE_GUIDE.md](VS_CODE_CONTINUE_GUIDE.md).
A repo-specific Chinese guide is available at [VS_CODE_CONTINUE_GUIDE_ZH.md](VS_CODE_CONTINUE_GUIDE_ZH.md).
For migration into another project, read [MIGRATION_GUIDE_ZH.md](MIGRATION_GUIDE_ZH.md).
For a ready-to-paste Chinese Continue prompt, use [prompts/continue_agent_zh.md](prompts/continue_agent_zh.md).

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
- If your USB-TTL adapter is not on `COM3`, update [agent_workbench.yaml](agent_workbench.yaml) before running hardware sessions.
