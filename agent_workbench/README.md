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
agent_workbench.bat context --mode debug --stage analyze
agent_workbench.bat context --mode feature --stage implement --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat context --mode feature --stage verify --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat context --stage resume
agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --command red on --command green on --command blue on --command all off
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
- `*_resume.md`: resume card for the next round
- `*_paste.md`: ready-to-paste Continue prompt
- `agent_state.json`: current mode, stage, profile, latest session, and next commands

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
3. Use `Terminal: Run Task` and the generated staged `Agent Workbench: ...` tasks.
4. Switch Continue to `Agent` mode.
5. Run a matching `Context Pack ...` task first.
6. Open the newest `*_paste.md` under `agent_workbench/runtime/`.
7. Paste only that stage card into Continue.
8. Have Continue drive actions through `agent_workbench.bat ...`, not ad-hoc shell command chains.

For immediate validation in PowerShell, prefer the one-command path:

```powershell
cmd /c ".\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml"
```

A repo-specific English guide is available at [VS_CODE_CONTINUE_GUIDE.md](VS_CODE_CONTINUE_GUIDE.md).
A repo-specific Chinese guide is available at [VS_CODE_CONTINUE_GUIDE_ZH.md](VS_CODE_CONTINUE_GUIDE_ZH.md).
For migration into another project, read [MIGRATION_GUIDE_ZH.md](MIGRATION_GUIDE_ZH.md).
For a ready-to-paste Chinese Continue prompt, use [prompts/continue_agent_zh.md](prompts/continue_agent_zh.md).
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
- If your USB-TTL adapter is not on `COM3`, update [agent_workbench.yaml](agent_workbench.yaml) before running hardware sessions.
