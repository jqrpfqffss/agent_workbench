# 测试流程

## 设计

1. 从用户需求、源码、CLI help/status 输出、硬件限制和历史 evidence 提取行为契约。
2. 先建立覆盖矩阵，再写或运行 probe。
3. 每个用例都映射到明确证据面：UART、diag、monitor、build 自检、remote-dt 或源码审查。
4. 定义稳定断言：稳定协议文本才用精确字符串；测量值用数值范围；计数器用单调/趋势；控制逻辑用状态迁移。

## 执行

1. `doctor --json`
2. `build --json`
3. 涉及实机行为时运行 `flash --json`，必要时 `reset --json`
4. `uart exec --reset-first --expect-ready --json` 和/或 `diag exec --json`
5. 涉及内部状态时更新 monitor YAML，并运行 `monitor start`、触发行为、`monitor stop`、`monitor stats`
6. 涉及远程 Linux 测试或覆盖率时运行 `remote-dt build/execute/coverage/pipeline/pull-logs --json`

## 改进

- probe 太弱时，增加更强 UART/diag 断言或 monitor item。
- evidence 不稳定时，降低时序敏感度，或增加 ready/liveness 检查。
- 源码行为错误时，修源码后先重跑最小失败用例。
- 环境阻塞 evidence 时，报告阻塞，不要宣称测试失败。
