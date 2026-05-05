---
name: agent-workbench-feature-zh
description: 当用户要在使用 agent_workbench 的 STM32 项目中新增功能、修改功能、扩展 CLI、增加外设控制、实现状态逻辑、控制环路、状态上报，或要求“实现并验证”时使用。本中文 skill 应与 agent-workbench-toolbox-zh 组合，通过项目发现、源码修改、build、flash、UART/diag/monitor 实机验证和 evidence 报告完成闭环。
---

# Agent Workbench 功能开发（中文）

用户要求新增、修改或验证固件行为时使用本 workflow：外设、CLI 命令、协议、状态逻辑、控制环路、状态上报，或“实现并验证”类工作。

始终与 `agent-workbench-toolbox-zh` 配合使用。

## 功能开发流程

1. 运行 `doctor --json`。
2. 运行 `scan-project --json`。
3. 读取现有源码和生成头文件，再决定硬件参数。
4. 如果需要紧凑上下文，运行 `context --mode feature --stage analyze --json`。
5. 做最小且完整的固件修改。
6. 运行 `build --json`；普通编译/链接失败才用 `fix-build --json`。
7. 需要真实硬件证据时直接 flash。
8. 用 UART/diag 命令验证用户可见行为。
9. 需要内部状态、寄存器、计数器或趋势证据时，由 OpenCode 修改 `agent_workbench/agent_workbench.yaml` 添加或更新 monitor items。
10. 长时间采样前先运行 `monitor probe --json`。
11. 运行 `verify current --json`，再运行 `report --latest --json`；回归对比时运行 `compare --latest --json`。
12. 按 [references/feature-report-template.md](references/feature-report-template.md) 输出功能报告。

## 按需读取

- 标准开发路径：[references/feature-flow.md](references/feature-flow.md)
- 实现方法论：[references/feature-development-methodology.md](references/feature-development-methodology.md)
- 验收模式：[references/feature-acceptance-patterns.md](references/feature-acceptance-patterns.md)
- 报告模板：[references/feature-report-template.md](references/feature-report-template.md)
- monitor 配置：`agent-workbench-toolbox-zh/references/monitor-configuration.md`

## 完成标准

功能不是 build 通过就完成。最终报告必须说明：

- 修改了什么。
- 为什么修改匹配当前项目的硬件和软件结构。
- build 已通过。
- 通过 UART/diag/monitor 获得了合适的实机证据。
- 涉及 CLI 时 ready/prompt 和命令响应稳定。
- 涉及内部状态时有 monitor 样本或寄存器读取证据。
- 剩余风险和精确 evidence 路径。
