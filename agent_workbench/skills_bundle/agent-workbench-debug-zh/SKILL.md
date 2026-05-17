---
name: agent-workbench-debug-zh
description: 当用户在使用 agent_workbench 的 STM32 项目中要求自动化调试、根因分析、串口无响应、ready/prompt 缺失、flash/reset 失败、运行时回归、monitor 采样失败、diag 失败、断言失败或故障恢复时使用。本中文 skill 应与 agent-workbench-toolbox-zh 组合，先走 evidence-first 分层排查，再决定是否改源码。
---

# Agent Workbench 自动化调试（中文）

用户要求调试、诊断、找根因、解释失败或恢复失败的 STM32 自动化运行时使用本 workflow。始终与 `agent-workbench-toolbox-zh` 配合使用。

## 调试流程

1. 运行 `doctor --json`，读取 `doctor_report.json/md`；阻塞性失败先报告，不改源码。
2. 用最小命令复现问题：build、flash/reset、UART、diag、monitor 或 remote-dt 中选择最窄证据面。
3. 涉及构建时运行 `build --json`；普通编译/链接失败才运行 `fix-build --json`。
4. 涉及固件版本或板上行为时运行 `flash --json`，必要时 `reset --json`。
5. 涉及 UART/CLI 时运行 `uart exec --reset-first --expect-ready --json`，再读 `tmp/uart_exec_result.json` 和 `cli_transcript.log`。
6. 涉及诊断协议时运行 `diag exec --json`，再读 `diag_exec_result.json` 和 `diag_exchange.log`。
7. 运行态不清楚时，修改 `agent_workbench/agent_workbench.yaml` 添加少量高信号 monitor items，运行 `monitor start` -> 触发动作 -> `monitor stop` -> `monitor stats`。
8. 需要远程 Linux/覆盖率/远程测试证据时，按配置运行 `remote-dt build/execute/coverage/pipeline/pull-logs --json`。
9. 先基于 evidence 给根因排序，再决定是否改源码。
10. 修复后重跑最小失败 probe，再跑一个覆盖相邻风险的回归 probe。
11. 按 [references/debug-report-template.md](references/debug-report-template.md) 输出调试报告。

## 按需读取

- 调试路径：[references/debug-flow.md](references/debug-flow.md)
- 调试方法论：[references/debug-methodology.md](references/debug-methodology.md)
- 实验设计手册：[references/debug-experiment-playbook.md](references/debug-experiment-playbook.md)
- 命令手册：[references/debug-command-playbook.md](references/debug-command-playbook.md)
- diag 分类线索：[references/diag-codes.md](references/diag-codes.md)
- evidence-first 根因排序：[references/evidence-first-root-cause.md](references/evidence-first-root-cause.md)
- 报告模板：[references/debug-report-template.md](references/debug-report-template.md)
- monitor 配置：`agent-workbench-toolbox-zh/references/monitor-configuration.md`

## 规则

除非 evidence 已经定位到源码层根因，否则不要一上来改代码。调试必须先分层：launcher、环境、build、flash/reset、UART RX/TX、ready/prompt、parser/CLI、diag、monitor/debug access、固件逻辑、remote-dt、回归。
