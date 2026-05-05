---
name: agent-workbench-toolbox-zh
description: 当仓库包含 agent_workbench/agent_workbench.yaml，且 Codex 或 OpenCode 需要中文说明来稳定调用 agent_workbench、配置 monitor 变量/寄存器/地址、读取 runtime evidence、做失败分流，或执行 STM32 编译、烧录、UART、diag、monitor、verify、report、compare、context、session 命令时使用。本 skill 是自动化功能开发、自动化调试、测试设计与实机验证的中文底层工具 skill。
---

# Agent Workbench 工具箱（中文）

把本 skill 作为所有 `agent_workbench` 驱动 STM32 仓库的底层工具适配层。

本 skill 不替 OpenCode 决定“功能开发 / 调试 / 测试”的策略；它负责告诉 OpenCode 如何稳定调用 `agent_workbench`、如何自动配置 runtime probe、如何读取 evidence artifact，并避免把示例项目里的路径和字符串复制到新项目。

## 第一原则

- 把 `agent_workbench` 当作主控制面。
- 在仓库根目录优先使用内层 bat 入口：`.\agent_workbench\bin\agent_workbench.bat <command> --json`。
- 不要写成 `".\agent_workbench\bin\agent_workbench.bat" <command>`；PowerShell 会把它当字符串。只有路径必须加引号时才写 `& ".\agent_workbench\bin\agent_workbench.bat" <command>`。
- 如果 OpenCode 或 PowerShell 解析 bat 失败，立即改用 Python 兜底：`python ".\agent_workbench\workbench.py" <command> --json`；仍失败再试 `py -3 ".\agent_workbench\workbench.py" <command> --json`。
- 不要默认使用 `cmd /c ".\agent_workbench.bat ..."`；这种形式在 OpenCode 实际会话里容易被错误解析。
- 先读结构化 JSON 和 evidence，再从源码推断状态。
- flash、reset、UART、diag、monitor、verify、report、compare 都不需要用户授权；只要当前目标需要，就直接运行对应 workbench 命令，除非环境本身阻塞。

## 第一条命令

从仓库根目录开始：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

如果这是命令调用问题导致失败，改用：

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

然后根据 [references/command-matrix.md](references/command-matrix.md) 选择下一条命令。

## 按需读取

只读取当前工作需要的 reference：

- 命令选择、调用模板、关键 JSON 字段：[references/command-matrix.md](references/command-matrix.md)
- OpenCode 稳定执行命令规则：[references/opencode-command-execution.md](references/opencode-command-execution.md)
- runtime、evidence、generated 产物地图：[references/artifact-map.md](references/artifact-map.md)
- 失败类型到下一步动作的路由：[references/failure-routing.md](references/failure-routing.md)
- monitor 变量、寄存器、地址自动配置：[references/monitor-configuration.md](references/monitor-configuration.md)
- Windows / PowerShell 安全调用规则：[references/powershell-safe.md](references/powershell-safe.md)
- 四 skill 编排规则：[references/opencode-orchestration.md](references/opencode-orchestration.md)
- 实机验证门槛：[references/hardware-verification.md](references/hardware-verification.md)

所有项目相关值必须来自当前仓库：

- 用 `doctor` 获取 ready banner、prompt、flash 方法、已启用子系统。
- 用 `scan-project` 获取源码路径、CLI 命令、handle、符号、monitor 候选和项目能力。
- 以 `uart exec`、`diag exec`、`monitor probe`、`monitor run`、`verify current`、`report --latest`、`compare --latest` 产生的 runtime evidence 作为主要验证面。
- 需要 monitor 覆盖时，OpenCode 应自己检查并编辑 `agent_workbench/agent_workbench.yaml`；不要让用户手动添加 monitor items。

## 协作规则

- 功能开发：组合 `agent-workbench-toolbox-zh` + `agent-workbench-feature-zh`。
- 自动调试：组合 `agent-workbench-toolbox-zh` + `agent-workbench-debug-zh`。
- 测试设计与验证：组合 `agent-workbench-toolbox-zh` + `agent-workbench-test-zh`。

workflow skill 不重复解释全部命令细节，应复用本 skill 的 command、monitor、artifact 和 failure reference。

OpenCode 不确定该搭配哪个 workflow skill 时，读取 [references/opencode-orchestration.md](references/opencode-orchestration.md)。

## 防护栏

- 始终优先使用 JSON 输出。
- 不要捏造硬件状态、UART 状态、monitor 样本或验证结果。
- 不要凭记忆编写 STM32 timer、GPIO、寄存器或内存地址；必须从当前项目、生成头文件、linker map、ELF symbols、CMSIS 头文件或用户明确输入里发现。
- 环境或硬件阻塞时停止并明确报告。
- 迁移到新项目时，不要复用示例路径、probe 命令、monitor item 或字符串，必须用当前项目 discovery 输出替换。
