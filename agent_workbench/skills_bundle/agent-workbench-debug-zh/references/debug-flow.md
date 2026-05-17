# 调试路径

## 快速路径

1. 运行 `doctor --json`。
2. 用最小失败命令复现。
3. 读取该命令 JSON 和 artifact。
4. 先分层，再修改。

## 显式路径

1. `doctor --json`
2. `build --json`
3. 如果板卡固件可能过期，运行 `flash --json`
4. 启动/复位症状用 `reset --json`
5. CLI 可见症状用 `uart exec --reset-first --expect-ready --json`
6. 诊断协议症状用 `diag exec --json`
7. 运行态不清楚时更新 monitor YAML，运行 `monitor start`，触发行为，运行 `monitor stop` 和 `monitor stats`
8. 远程 Linux/覆盖率/远端流水线症状用 `remote-dt ... --json`

## 停止条件

- 环境阻塞：报告精确 doctor 失败，不改源码。
- 硬件阻塞：报告 flash/reset/debug connection/COM 占用证据。
- 命令启动失败：用 direct Python 兜底重试一次，仍失败就报告。
- evidence 冲突：设计更窄的 probe，不猜。
