# Agent Workbench

`agent_workbench/` is the automation control plane for this STM32 UART CLI project.

It is not just a loose script bundle. It provides one stable entry point for:

- environment checks
- CMake build
- flash and reset
- UART CLI probing
- diagnostic UART raw hex exchanges
- monitor capture
- automated debug sessions
- automated feature validation sessions
- report and compare generation
- VS Code task generation

For this repository, the current board-facing defaults are:

- project: `serial`
- build output: `build/cmake-debug/serial.elf`
- UART console: `USART2 / PA2(TX) / PA3(RX) / 115200 8N1`
- diagnostic UART smoke target: `COM3 / 115200 8N1 / raw hex`
- ready banner: `STM32 UART CLI ready.`
- prompt: `cli>`

The single source of truth is [agent_workbench.yaml](agent_workbench.yaml).

## Layout

- `agent_workbench.yaml`: project, tools, outputs, UART, diagnostic UART, prompts, and workflow config
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

To enable the new Continue auto-mode rules, also run:

```powershell
agent_workbench.bat init-continue-rules
```

## Main Commands

```powershell
agent_workbench.bat doctor
agent_workbench.bat doctor --json
agent_workbench.bat build
agent_workbench.bat build --json
agent_workbench.bat flash --method stlink_cli
agent_workbench.bat flash --method openocd_cmd
agent_workbench.bat reset --method stlink_cli
agent_workbench.bat scan-project --json
agent_workbench.bat plan "give the board a 1Hz LED blink" --json
agent_workbench.bat parse-errors --json
agent_workbench.bat ps-exec "build"
agent_workbench.bat context --mode debug --stage analyze
agent_workbench.bat context --mode feature --stage implement --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat context --mode feature --stage verify --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat context --stage resume
agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --command red on --command green on --command blue on --command all off
agent_workbench.bat diag exec
agent_workbench.bat diag exec --hex "68 65 6C 70 0D 0A" --hex "73 74 61 74 75 73 0D 0A"
agent_workbench.bat diag exec --script agent_workbench\runtime\diag_requests.txt
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
agent_workbench.bat init-continue-rules
```

## Continue Auto Mode

The workbench now supports a plan-first auto workflow for Continue:

1. Generate repo rules with `agent_workbench.bat init-continue-rules`.
2. In Continue Agent, ask for a feature or debug task in one sentence.
3. Continue should start from `agent_workbench.bat plan "<request>" --json`.
4. It then reads the returned `steps[]`, edits only allowed files, and uses JSON command outputs for build/flash/UART verification.

The generated rules are written to `.continue/rules/`:

- `stm32_auto_workflow.md`
- `stm32_weak_model_guard.md`
- `stm32_powershell_syntax.md`
- `stm32_error_recovery.md`
- `stm32_hardware_safety.md`
- `stm32_model_deepseek_r1.md`
- `stm32_model_qwen7b.md`
- `stm32_model_glm.md`

The auto-mode planner is backed by:

- `agent_workbench/templates/task_templates/`
- `agent_workbench.bat plan`
- `agent_workbench.bat scan-project`
- `agent_workbench.bat parse-errors`
- `agent_workbench.bat ps-exec`

The current template catalog covers 16 common STM32 task shapes, including GPIO, timer, PWM, ADC, EXTI, interrupt handler, DMA, I2C, SPI, UART echo, CLI command, sensor polling, fault diagnosis, and monitor/watch workflows.

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
- `deepseek_r1`
- `qwen7b`
- `glm`

The staged VS Code tasks and `context` flow use `agent.default_profile` by default. You only need `--profile ...` when you want to temporarily override the configured default.

## Regression And Validation

Second-stage stability work now includes:

- template-library regression coverage under `agent_workbench/tests/test_planner_regression_suite.py`
- project scanner regression coverage under `agent_workbench/tests/test_project_scanner.py`
- structured compiler fix rules in `agent_workbench/templates/build_error_rules.json`
- richer UART failure classification in `cli_diag.json`

Recommended smoke checks after migration or rule updates:

```powershell
agent_workbench.bat scan-project --json
agent_workbench.bat plan "增加 I2C 传感器寄存器读取" --json
agent_workbench.bat init-continue-rules --json
agent_workbench.bat doctor --json
py -3.8 -m unittest discover -s agent_workbench/tests -p "test_*.py"
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

## Diagnostic UART Hex Flow

The workbench now supports a second host-side UART path for raw hex exchanges:

- config block: `diag_uart` in [agent_workbench.yaml](agent_workbench.yaml)
- default log: `agent_workbench/runtime/diag_exchange.log`
- default result JSON: `agent_workbench/runtime/diag_exec_result.json`

The current repository uses the same `COM3` debug CLI port as the temporary validation target. That lets us validate the host-side diagnostic tooling without changing the STM32 firmware. The default requests send `help\r\n` and `status\r\n` as hex:

```powershell
agent_workbench.bat diag exec
```

You can also send explicit requests:

```powershell
agent_workbench.bat diag exec --hex "68 65 6C 70 0D 0A"
agent_workbench.bat diag exec --hex "73 74 61 74 75 73 0D 0A"
```

Each exchange records both hex and escaped text preview so ASCII replies stay readable while binary payloads remain inspectable.

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
For the new Chinese auto-mode walkthrough, read [CONTINUE_AUTO_MODE_GUIDE_ZH.md](CONTINUE_AUTO_MODE_GUIDE_ZH.md).
For a ready-to-paste Chinese Continue prompt, use [prompts/continue_agent_zh.md](prompts/continue_agent_zh.md).
For the current project's one-command verification prompt, use [prompts/continue_verify_current_zh.md](prompts/continue_verify_current_zh.md).
For low-context local models, read [LOW_CONTEXT_MODELS_GUIDE_ZH.md](LOW_CONTEXT_MODELS_GUIDE_ZH.md) and use [prompts/continue_low_context_zh.md](prompts/continue_low_context_zh.md).

## Evidence-First Workflow

For debug and feature work, conclusions should be based on generated evidence, not only source inspection.

Primary evidence files:

- `cli_transcript.log`
- `cli_diag.json`
- `diag_exchange.log`
- `diag_exec_result.json`
- `uart.log`
- `monitor_samples.csv`
- `assertions.jsonl`
- `session_summary.md`
- `feature_summary.md`
- `compare_vs_*.md`

## Notes

- `uart console` still works best with `pyserial` available in the Python environment.
- If `pyserial` is unavailable, the workbench still supports PowerShell fallback for `uart exec`, `uart run`, and session logging.
- If your USB-TTL adapter is not on `COM3`, update both `uart.port` and `diag_uart.port` in [agent_workbench.yaml](agent_workbench.yaml) before running hardware sessions.
