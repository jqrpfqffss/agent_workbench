# OpenCode 编排规则

大多数工作只使用两个 skill：

- 功能实现：`agent-workbench-toolbox-zh` + `agent-workbench-feature-zh`。
- 自动调试：`agent-workbench-toolbox-zh` + `agent-workbench-debug-zh`。
- 测试设计与验证：`agent-workbench-toolbox-zh` + `agent-workbench-test-zh`。

避免四个 workflow 一次性全加载。先根据用户主要意图选择一个 workflow；工作阶段改变时再切换。

## 默认 OpenCode 循环

1. 发现：`doctor --json`、`scan-project --json`。
2. 检查：读取当前源码、生成头文件、配置和已有 evidence。
3. 执行：修改源码；需要 monitor 覆盖时修改 `agent_workbench/agent_workbench.yaml`。
4. 构建：`build --json`，失败时小步修复。
5. 实机：flash、UART、diag、monitor。
6. 汇总：`verify current --json`、`report --latest --json`，需要时 `compare --latest --json`。
7. 报告：给出 artifact 路径和剩余风险。

## 实用规则

- 使用 OpenCode 自身规划能力做拆解；不要依赖旧 plan 输出。
- `agent_workbench/tests/*.py` 是 workbench 平台自测，只在修改平台本身时有用，不用于验证迁移项目固件功能。
- 迁移项目默认依赖源码发现和 runtime evidence，不依赖项目专属生成资产。
- 需要 monitor 证据时，OpenCode 应自动修改 YAML 并用 `monitor probe` 验证。
- evidence 与源码预期冲突时，先相信 evidence，再设计下一条窄 probe。
