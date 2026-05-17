---
name: agent-workbench-dt-test-zh
description: 当用户在 agent_workbench 管理的 STM32 项目中要求编写、完善、迁移、审查或执行 DT 测试用例，尤其是 remote-dt 远程 Linux 构建/执行/覆盖率流水线、execute.sh 测试入口、DT case matrix、覆盖率门槛、远端日志/JSON 证据闭环时使用。本中文 skill 只允许使用五条 remote-dt 命令：remote-dt build、execute、coverage、pipeline、pull-logs，均必须带 --json。
---

# Agent Workbench DT 测试用例（中文）

本 skill 专注“写出并验证 DT 测试用例”。DT 在这里指 `remote-dt` 驱动的远程开发/测试流水线，不是 Devicetree。

本 skill 是自包含的 remote-dt workflow。除下列五条命令外，不运行其它 workbench 命令。

## 允许命令

只使用以下五条命令，且每次只运行一条：

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt build --json
.\agent_workbench\bin\agent_workbench.bat remote-dt execute --json
.\agent_workbench\bin\agent_workbench.bat remote-dt coverage --json
.\agent_workbench\bin\agent_workbench.bat remote-dt pipeline --json
.\agent_workbench\bin\agent_workbench.bat remote-dt pull-logs --json
```

## 核心流程

1. 读取当前 DT 需求、已有 DT 用例、`agent_workbench/agent_workbench.yaml` 的 `remote_dt` 配置、远端脚本约定和已有 `agent_workbench/runtime/remote_dt/*` evidence。
2. 先写行为契约，再写用例：远端入口、触发、期望、remote-dt 观测面、失败诊断线索、覆盖率目标。
3. 优先复用项目已有远端测试框架和目录；没有约定时，只创建最小、清晰、非交互式的 DT 用例入口，并把它接入 `remote_dt.scripts.execute` 指向的脚本。
4. 需要远端构建验证时运行 `remote-dt build --json`；需要执行用例时运行 `remote-dt execute --json`；需要覆盖率时运行 `remote-dt coverage --json`；需要完整闭环时运行 `remote-dt pipeline --json`；只需要重新取证时运行 `remote-dt pull-logs --json`。
5. 分析 `dt_remote_result.json`、`dt_remote_summary.md`、`logs/dt_*.log`、`results/dt_*_result.json` 和 `coverage/`，不要只看命令摘要。
6. 输出每个 DT 用例的目标、断言、证据 artifact、pass/fail/blocked 和未覆盖风险。

## 边界

- 不把 `agent_workbench/tests/*.py` 当作目标固件或业务 DT 用例，除非正在修改 workbench 平台本身。
- 不假设远端代码已经同步；remote-dt 不负责同步源码。无法确认时，把远端执行标为 blocked，并说明需要同步。
- 不臆测硬件参数、寄存器地址、内存地址、GPIO/TIM/ADC 配置；必须来自当前源码、生成文件、远端测试 harness、覆盖率报告或 remote-dt evidence。
- 不用长段自然语言、时间戳、随机 ID、地址值做脆弱断言。

## 按需读取

- 设计高质量 DT 用例时读 [references/dt-case-methodology.md](references/dt-case-methodology.md)。
- 需要落地用例文件、矩阵或结果格式时读 [references/dt-case-template.md](references/dt-case-template.md)。
- 需要接入或验证 remote-dt 脚本时读 [references/remote-dt-contract.md](references/remote-dt-contract.md)。
- 需要选择 remote-dt 阶段、日志断言、结构化结果或覆盖率断言时读 [references/dt-case-patterns.md](references/dt-case-patterns.md)。
- 需要让 OpenCode 稳定执行、不跑偏时读 [references/opencode-guardrails.md](references/opencode-guardrails.md)。

## 完成标准

一次 DT 用例任务完成时，至少满足：

- 用例覆盖正常路径、边界/非法输入、错误恢复、关键回归风险和覆盖率目标中的相关项。
- 每个用例都有明确 remote-dt 观测面：阶段 result JSON、阶段 log、结构化 case verdict 或 coverage artifact。
- 已执行必要的 remote-dt 命令并报告 exit_code；未执行的远端验证必须明确 blocked。
- 最终报告列出真实 remote-dt 命令、exit_code、artifact 路径和失败阶段。
