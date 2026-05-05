# 实机验证门槛

涉及真实固件行为时，不能只用 build 成功作为结论。

## 最小闭环

1. `doctor --json` 确认可用环境。
2. `build --json` 成功。
3. `flash --json` 将当前固件烧录到板卡。
4. `uart exec ... --json` 或 `diag exec ... --json` 验证外部可见行为。
5. 需要内部状态、寄存器或趋势时，自动配置 monitor items，然后运行 `monitor probe --json` 或 `monitor run --json`。
6. `verify current --json` 或 `report --latest --json` 给出 verdict/summary。

## 何时必须 monitor

- 用户要求证明变量、状态机、计数器、寄存器、内存地址、控制输出或趋势。
- UART 只显示“命令成功”，但不能证明内部状态已经变化。
- debug 需要区分命令未触发、状态未更新、输出未生效、采样链路失败。

## 报告要求

最终报告至少包含 build、flash、UART/diag、monitor（如使用）、verify/report 的关键证据路径。
