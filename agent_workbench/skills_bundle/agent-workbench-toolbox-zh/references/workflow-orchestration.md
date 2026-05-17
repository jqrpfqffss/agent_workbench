# Workflow 编排规则

大多数任务只加载工具箱加一个 workflow skill，避免一次性加载所有说明。

- 功能实现：`agent-workbench-toolbox-zh` + `agent-workbench-feature-zh`。
- 自动调试：`agent-workbench-toolbox-zh` + `agent-workbench-debug-zh`。
- 测试设计与验证：`agent-workbench-toolbox-zh` + `agent-workbench-test-zh`。

## 默认循环

1. 发现：运行 `doctor --json`，读取当前配置、ready/prompt、artifact、UART/diag/monitor 可用性。
2. 定位：读取当前源码、生成头文件、linker/map、ELF symbols 和已有 runtime artifacts。
3. 修改：只改与目标相关的源码或 `agent_workbench/agent_workbench.yaml`。
4. 构建：运行 `build --json`；普通编译/链接失败时运行 `fix-build --json` 并小步修复，最多 3 轮。
5. 实机：需要板上证据时运行 `flash --json`、`reset --json`，再用 UART/diag/monitor 采集 evidence。
6. 报告：列出真实命令、exit_code、artifact 路径、结论和剩余风险。

## 实用规则

- `agent_workbench/tests/*.py` 是 Agent Workbench 平台自测；除非修改平台本身，否则不用它验证迁移项目固件。
- monitor 证据需要先编辑 YAML，再用 `monitor start`、触发动作、`monitor stop`、`monitor stats` 验证样本。
- evidence 与源码预期冲突时，先相信 evidence，再设计下一条窄 probe。
