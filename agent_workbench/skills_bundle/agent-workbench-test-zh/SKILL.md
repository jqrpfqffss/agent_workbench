---
name: agent-workbench-test-zh
description: 当用户在使用 agent_workbench 的 STM32 项目中要求通用测试设计、测试用例生成、回归探测、断言规划、自动化验证、失败分析或实机验证时使用。本中文 skill 应与 agent-workbench-toolbox-zh 组合，从当前源码行为和 runtime evidence 设计高质量测试，再用 build、flash、UART、diag、monitor 完成验证。若用户明确要求 DT 测试用例、remote-dt 流水线、远程 Linux 执行或覆盖率闭环，优先改用 agent-workbench-dt-test-zh。
---

# Agent Workbench 测试设计与验证（中文）

用户要求测试用例、回归覆盖、断言、验证、失败分析或实机验证时使用本 workflow。始终与 `agent-workbench-toolbox-zh` 配合使用。明确要求 DT 用例或 remote-dt 时，使用 `agent-workbench-dt-test-zh`。

## 测试流程

1. 运行 `doctor --json`，读取当前配置和可用验证面。
2. 从源码、CLI help/status、用户需求、已有 evidence 和硬件约束提取行为契约。
3. 建立覆盖矩阵：正常路径、边界值、非法输入、状态迁移、reset 行为、必要时的持久化、时序/趋势、回归探针。
4. 为每个用例选择证据面：UART 命令、diag 交换、monitor item、build 自检、remote-dt，或源码/配置审查。
5. 需要 monitor 证据时，自动修改 `agent_workbench/agent_workbench.yaml`，然后运行 `monitor start` -> 触发行为 -> `monitor stop` -> `monitor stats`。
6. 运行 `build --json`；需要实机验证时运行 `flash --json`，然后执行 UART/diag/monitor 证据闭环。
7. 需要远程 Linux 测试、DT 用例或覆盖率时，切换到 `agent-workbench-dt-test-zh`，再运行相应 `remote-dt ... --json`。
8. 失败时先判断测试设计、probe、证据面、环境/硬件、源码行为哪个层面出错。
9. 按 [references/test-report-template.md](references/test-report-template.md) 输出测试报告。

## 按需读取

- 端到端测试路径：[references/test-flow.md](references/test-flow.md)
- 测试设计方法论：[references/test-design-methodology.md](references/test-design-methodology.md)
- 覆盖矩阵：[references/test-coverage-matrix.md](references/test-coverage-matrix.md)
- 断言模式：[references/assertion-patterns.md](references/assertion-patterns.md)
- 失败归因：[references/test-failure-triage.md](references/test-failure-triage.md)
- 报告模板：[references/test-report-template.md](references/test-report-template.md)
- monitor 配置：`agent-workbench-toolbox-zh/references/monitor-configuration.md`

## 质量标准

好的 STM32 测试必须 evidence-driven：

- 尽量断言外部可见行为。
- 内部状态只通过明确设计的 monitor items 观察。
- 覆盖边界、非法输入、reset/restart 和回归风险。
- 除 ready/prompt/help/status 等稳定文本外，避免脆弱字符串断言。
- 精确报告每个用例由哪份 evidence 证明、否定或阻塞。
