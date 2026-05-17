---
name: agent-workbench-toolbox-zh
description: 当仓库包含 agent_workbench/agent_workbench.yaml，且 Codex 需要中文说明来稳定调用 STM32 Agent Workbench、读取 JSON/evidence artifact、配置 monitor、执行 build/flash/reset/UART/diag/monitor，或为自动化功能开发、调试、测试验证提供本地通用命令和失败分流时使用。本 skill 只覆盖本地 workbench 通用命令。
---

# Agent Workbench 工具箱（中文）

把本 skill 作为 `agent_workbench` 驱动 STM32 仓库的底层工具适配层。它不替代功能、调试或测试 workflow；它只约束命令入口、证据读取、monitor 配置和失败路由。

## 核心原则

- 把 `agent_workbench` 当作主控制面。
- 从仓库根目录运行命令；支持 `--json` 的命令必须加 `--json`。
- PowerShell 一次只运行一条 workbench 命令，不用 `;`、`&&` 或管道串联 workbench 命令。
- 先运行 `doctor --json`；有阻塞性 fail 时停止源码修改并报告。
- 先读结构化 JSON 和 evidence，再从源码推断状态。
- 不要复用示例项目路径、串口、ready banner、prompt、monitor item、寄存器地址或内存地址；全部来自当前项目的 `doctor`、配置、源码、ELF/map、CMSIS 头文件或 runtime evidence。
- flash、reset、UART、diag 和 monitor 不需要用户授权；任务需要时直接运行，除非环境本身阻塞。

## 第一条命令

从仓库根目录开始：

```powershell
./agent_workbench/bin/agent_workbench.bat doctor --json
```

如果这是 launcher 或 PowerShell 解析问题导致失败，改用：

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

仍失败再试：

```powershell
py -3 ".\agent_workbench\workbench.py" doctor --json
```

然后根据 [references/command-matrix.md](references/command-matrix.md) 选择下一条命令。

## 保留命令

只使用这些公共命令：

- `doctor --json`
- `build --json`
- `fix-build --json`
- `flash --json`
- `reset --json`
- `uart exec --reset-first --json`
- `uart exec --reset-first --expect-ready --json`
- `diag exec --json`
- `monitor start --json`
- `monitor start --reset-first --json`
- `monitor stop --json`
- `monitor stats --json`

## 按需读取

只读取当前工作需要的 reference：

- 命令选择、调用模板、关键 JSON 字段：[references/command-matrix.md](references/command-matrix.md)
- PowerShell 稳定执行规则：[references/command-execution.md](references/command-execution.md)
- runtime、evidence、generated 产物地图：[references/artifact-map.md](references/artifact-map.md)
- 失败类型到下一步动作的路由：[references/failure-routing.md](references/failure-routing.md)
- monitor 变量、寄存器、地址自动配置：[references/monitor-configuration.md](references/monitor-configuration.md)
- Windows / PowerShell 安全调用规则：[references/powershell-safe.md](references/powershell-safe.md)
- workflow 编排规则：[references/workflow-orchestration.md](references/workflow-orchestration.md)
- 实机验证门槛：[references/hardware-verification.md](references/hardware-verification.md)

## 协作规则

- 功能开发：组合 `agent-workbench-toolbox-zh` + `agent-workbench-feature-zh`。
- 自动调试：组合 `agent-workbench-toolbox-zh` + `agent-workbench-debug-zh`。
- 测试设计与验证：组合 `agent-workbench-toolbox-zh` + `agent-workbench-test-zh`。

workflow skill 不重复解释全部命令细节，应复用本 skill 的 command、monitor、artifact 和 failure reference。

不确定该搭配哪个 workflow skill 时，读取 [references/workflow-orchestration.md](references/workflow-orchestration.md)。

## 完成报告底线

最终报告只引用真实执行过的命令和真实 artifact。列出每条 workbench 命令的 `exit_code`、关键结论和 artifact 路径；未执行的实机验证写明“未执行”或具体阻塞原因。
