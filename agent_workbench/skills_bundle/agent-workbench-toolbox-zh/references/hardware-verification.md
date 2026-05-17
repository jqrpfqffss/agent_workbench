# 实机验证门槛

涉及真实固件行为时，不能只用 build 成功作为结论。

## 最小闭环

1. `doctor --json` 确认可用环境。
2. `build --json` 成功。
3. `flash --json` 将当前固件烧录到板卡。
4. 必要时 `reset --json` 建立启动证据。
5. `uart exec ... --json` 或 `diag exec --json` 验证外部可见行为。
6. 需要内部状态、寄存器或趋势时，配置 monitor items，然后运行 `monitor start` -> 触发行为 -> `monitor stop` -> `monitor stats`。

## 何时必须 monitor

- 用户要求证明变量、状态机、计数器、寄存器、内存地址、控制输出或趋势。
- UART 只显示“命令成功”，但不能证明内部状态已经变化。
- debug 需要区分命令未触发、状态未更新、输出未生效、采样链路失败。

## 阻塞处理

- `doctor` 报端口占用、OpenOCD、flash 或 monitor 失败时，报告环境/硬件阻塞。
- 如果 build 能通过但 COM 口被占用，不要宣称实机通过。
## 报告要求

最终报告至少包含实际执行的 build、flash/reset、UART/diag、monitor（如使用）的命令、exit_code 和 artifact 路径。
