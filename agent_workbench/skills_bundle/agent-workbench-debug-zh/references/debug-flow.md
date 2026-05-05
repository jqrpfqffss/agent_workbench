# 调试路径

## 快速路径

1. 用最小失败命令复现。
2. 可用时运行 `verify current --json`。
3. 读取 `direct_verify_summary.json`、`cli_diag.json`、`cli_transcript.log` 和本次运行引用的 monitor artifacts。
4. 先分层，再修改。

## 显式路径

1. `doctor --json`
2. `build --json`
3. 如果板卡固件可能过期，运行 `flash --json`
4. CLI 可见症状用 `uart exec ... --json`
5. 诊断协议症状用 `diag exec ... --json`
6. 运行态不清楚时更新 monitor YAML，再运行 `monitor probe --json`
7. `session debug --json`
8. `report --latest --json`
9. `compare --latest --json`

## 停止条件

- 环境阻塞：报告精确 doctor 失败，不改源码。
- 硬件阻塞：报告 flash/reset/debug connection 证据。
- 命令启动失败：用 direct Python 兜底重试一次，仍失败就报告。
- evidence 冲突：设计更窄的 probe，不猜。
