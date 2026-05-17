---
name: agent-workbench-feature-zh
description: 当用户要在使用 agent_workbench 的 STM32 项目中新增功能、修改功能、扩展 CLI、增加外设控制、实现状态逻辑、控制环路、状态上报，或要求“实现并验证”时使用。本中文 skill 应与 agent-workbench-toolbox-zh 组合，通过当前项目事实发现、源码修改、build、flash、UART/diag/monitor/remote-dt 实机或流水线证据完成闭环。
---

# Agent Workbench 功能开发（中文）

用户要求新增、修改或验证固件行为时使用本 workflow：外设、CLI 命令、协议、状态逻辑、控制环路、状态上报，或“实现并验证”类工作。始终与 `agent-workbench-toolbox-zh` 配合使用。

## 功能开发流程

1. 运行 `doctor --json`，阻塞性失败先报告。
2. 读取当前 `agent_workbench/agent_workbench.yaml`、README/配置、相关源码、生成头文件、linker/map、ELF symbols 和已有 runtime artifacts。
3. 从当前项目确认 ready banner、prompt、CLI 命令、source dirs、artifact、串口、flash 方法和 monitor/remote-dt 可用性；不要复用示例值。
4. 把需求拆成控制入口、状态变化、硬件资源、可观测证据和回归风险。
5. 做最小且完整的固件修改；生成代码优先在 USER CODE 或项目已采用的安全区域修改。
6. 运行 `build --json`；普通编译/链接失败才运行 `fix-build --json`，最多 3 轮。
7. 需要板上证据时运行 `flash --json`，必要时 `reset --json`。
8. 用 `uart exec --reset-first --expect-ready --json` 或 `diag exec --json` 验证用户可见行为。
9. 需要内部状态、寄存器、计数器或趋势证据时，自动修改 monitor YAML，运行 `monitor start` -> 触发行为 -> `monitor stop` -> `monitor stats`。
10. 需要远端 Linux/覆盖率/远程设备测试时，运行相应 `remote-dt ... --json`。
11. 按 [references/feature-report-template.md](references/feature-report-template.md) 输出功能报告。

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
- build 是否通过。
- 是否通过 UART/diag/monitor/remote-dt 获得合适证据。
- 涉及 CLI 时 ready/prompt 和命令响应是否稳定。
- 涉及内部状态时是否有 monitor 样本或明确阻塞原因。
- 剩余风险和精确 evidence 路径。
