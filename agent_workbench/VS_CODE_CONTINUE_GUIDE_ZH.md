# VS Code + Continue Agent 中文使用教程

## 1. 目标

这份教程用于把当前仓库配置成一套真正可落地的工作流，让 VS Code 配合 Continue 的 `Agent` 模式，通过 `agent_workbench` 完成：

- 自动化调试
- 自动化测试生成与执行
- 自动化功能验证
- 证据驱动的问题闭环

核心原则只有三条：

1. 统一通过 `agent_workbench.bat ...` 驱动自动化动作
2. 先读证据，再改代码
3. 修改后必须重新验证

## 2. 你会用到哪些东西

仓库里已经准备好的入口有：

- `agent_workbench.bat`
- `setup_workbench.bat`
- `agent_workbench/agent_workbench.yaml`
- `agent_workbench/prompts/continue_agent_zh.md`
- `agent_workbench/tasks/*.yaml`
- `.vscode/tasks.json`

其中唯一长期配置源是：

- `agent_workbench/agent_workbench.yaml`

## 3. 一次性准备

在 VS Code 打开项目根目录：

```powershell
H:\stm32_RAG\code\serial
```

先执行：

```powershell
setup_workbench.bat
agent_workbench.bat doctor
agent_workbench.bat init-vscode
```

执行完成后，你会得到：

- 项目入口脚本 `agent_workbench.bat`
- VS Code 任务文件 `.vscode/tasks.json`
- 当前环境检查结果 `agent_workbench/runtime/doctor_report.md`

## 4. 当前项目默认配置

当前 workbench 已对齐到这个 `serial` 项目：

- 构建目录：`build/cmake-debug`
- ELF：`build/cmake-debug/serial.elf`
- UART：`USART2 / PA2(TX) / PA3(RX) / 115200 8N1`
- ready banner：`STM32 UART CLI ready.`
- prompt：`cli>`
- 默认 probe 命令：
  - `help`
  - `status`
  - `red on`
  - `green on`
  - `blue on`
  - `all off`

如果你的 USB-TTL 不是 `COM3`，只改这里：

- `agent_workbench/agent_workbench.yaml`

## 5. VS Code 里怎么操作

在 VS Code 中按：

`Terminal -> Run Task`

你会看到这些工作台任务：

- `Agent Workbench: Setup`
- `Agent Workbench: Doctor`
- `Agent Workbench: Build`
- `Agent Workbench: UART CLI Smoke`
- `Agent Workbench: Debug Session`
- `Agent Workbench: Test Generate (CLI Regression)`
- `Agent Workbench: Test Run`
- `Agent Workbench: Feature Session (CLI Regression)`
- `Agent Workbench: Compare Latest`

推荐顺序：

### 调试场景

1. `Agent Workbench: Doctor`
2. `Agent Workbench: Build`
3. `Agent Workbench: UART CLI Smoke`
4. `Agent Workbench: Debug Session`
5. `Agent Workbench: Compare Latest`

### 功能场景

1. `Agent Workbench: Doctor`
2. `Agent Workbench: Build`
3. `Agent Workbench: Test Generate (CLI Regression)`
4. 让 Continue Agent 实现最小代码改动
5. `Agent Workbench: Test Run`
6. `Agent Workbench: Feature Session (CLI Regression)`
7. `Agent Workbench: Compare Latest`

## 6. Continue Agent 模式怎么用

在 VS Code 中：

1. 打开 Continue 面板
2. 切换到 `Agent` 模式
3. 把仓库里的中文模板直接粘进去

推荐直接使用：

- `agent_workbench/prompts/continue_agent_zh.md`

这个文件里已经给了四类可直接粘贴的模板：

- 通用总控模板
- 自动化调试模板
- 自动化功能实现模板
- 自动化测试资产模板
- 自动化报告模板

## 7. 最推荐的 Continue 用法

### 做自动化调试时

把 `continue_agent_zh.md` 里的“自动化调试模板”直接粘给 Continue。

Continue 应该做的事情是：

1. 先读 `agent_workbench.yaml`
2. 再读最新 evidence
3. 再执行 `doctor -> build -> uart exec -> session debug -> compare`
4. 先基于证据判断问题位置
5. 必要时才做最小代码修改
6. 修改后重新跑验证

### 做自动化功能验证时

把“自动化功能实现模板”粘给 Continue，并把 `<TASK>` 替换成实际 task 文件。

Continue 应该做的事情是：

1. 先读 task yaml
2. 再读 generated 测试资产
3. 先跑 `test generate` 和 `test run`
4. 再做最小代码改动
5. 最后跑 `session feature`

### 做自动化测试时

把“自动化测试资产模板”粘给 Continue。

Continue 应该优先操作：

- `agent_workbench/tasks/`
- `agent_workbench/generated/tasks/`
- `agent_workbench/tests/`

## 8. 自动化调试闭环

下面这组命令就是标准 debug loop：

```powershell
agent_workbench.bat doctor
agent_workbench.bat build
agent_workbench.bat flash
agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --command "red on" --command "green on" --command "blue on" --command "all off"
agent_workbench.bat session debug
agent_workbench.bat compare --latest
```

你应该重点看这些证据：

- `cli_transcript.log`
- `cli_diag.json`
- `uart.log`
- `session_summary.md`
- `compare_vs_*.md`

如果 CLI 握手失败，先看 `cli_diag.json` 的分类：

- `rx_zero`
- `parser_no_command`
- `tx_or_host_rx`
- `ready_missing`
- `prompt_missing`

## 9. 自动化测试闭环

生成测试资产：

```powershell
agent_workbench.bat test generate --task agent_workbench\tasks\cli_automation_regression.yaml
```

运行测试：

```powershell
agent_workbench.bat test run
```

输出会在：

- `agent_workbench/generated/tasks/<task_id>/`

常见文件包括：

- `blackbox_assertions.yaml`
- `unit_test_plan.md`
- `*_host_test_skeleton.c`

## 10. 自动化功能验证闭环

标准 feature loop：

```powershell
agent_workbench.bat doctor
agent_workbench.bat build
agent_workbench.bat test generate --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat test run
agent_workbench.bat session feature --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat compare --latest
```

你应该重点读：

- `feature_summary.md`
- `session_summary.md`
- `assertions.jsonl`
- `cli_transcript.log`
- `compare_vs_*.md`

## 11. 证据文件优先级

Continue 和人工都应该优先看这些文件，而不是先猜代码：

- `agent_workbench/evidence/sessions/<session>/cli_transcript.log`
- `agent_workbench/evidence/sessions/<session>/cli_diag.json`
- `agent_workbench/evidence/sessions/<session>/uart.log`
- `agent_workbench/evidence/sessions/<session>/assertions.jsonl`
- `agent_workbench/evidence/sessions/<session>/session_summary.md`
- `agent_workbench/evidence/sessions/<session>/feature_summary.md`
- `agent_workbench/evidence/sessions/<session>/compare_vs_*.md`

## 12. 推荐给 Continue 的固定要求

你可以要求 Continue 始终遵守这几条：

```text
1. 不要绕开 agent_workbench.bat 直接拼接零散命令。
2. 先读 evidence，再分析，再改代码。
3. 修改代码后必须重新验证。
4. 结论必须引用 evidence 文件。
5. 如果证据不够，明确说明缺的是什么。
```

## 13. 常见问题

### 1. `uart exec` 失败怎么办

先看：

- `agent_workbench/runtime/cli_transcript.log`
- `agent_workbench/runtime/cli_diag.json`

### 2. 为什么手动串口能通，但 workbench 失败

优先检查：

- `agent_workbench.yaml` 中的 `uart.port`
- 当前串口是否被别的工具占用
- ready banner / prompt 是否与配置一致
- workbench 生成的 transcript 是否捕获到了实际输出

### 3. `cli_diag.json` 成功时为什么可能没有

成功的 smoke / feature session 不一定需要生成 `cli_diag.json`。它主要服务于失败诊断。成功时没有这个文件是正常的。

### 4. `uart console` 为什么还可能提示 pyserial

当前仓库已经支持 PowerShell fallback 做 `uart exec` 和 session 日志，但交互式 `uart console` 仍然更依赖 `pyserial`。

## 14. 推荐入口

如果你现在就要开始用，最省事的入口是：

1. 先运行 `Agent Workbench: Doctor`
2. 再运行 `Agent Workbench: Build`
3. 把 `agent_workbench/prompts/continue_agent_zh.md` 里的模板粘给 Continue Agent
4. 让 Continue 严格通过 `agent_workbench.bat` 推进

## 15. 相关文件

- `agent_workbench/README.md`
- `agent_workbench/agent_workbench.yaml`
- `agent_workbench/prompts/continue_agent_zh.md`
- `agent_workbench/prompts/continue_debug.md`
- `agent_workbench/prompts/continue_feature.md`
- `agent_workbench/prompts/continue_test_author.md`
- `agent_workbench/prompts/continue_report.md`
