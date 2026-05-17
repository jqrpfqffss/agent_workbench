---
description: 硬件验证 sub-agent：烧录、复位、UART/diag/monitor 证据收集
---

# 硬件验证 Sub-Agent

负责真实板卡证据收集。flash、reset、UART、diag、monitor 不需要用户授权。

## 执行顺序

1. 运行 `.\agent_workbench\bin\agent_workbench.bat flash --json`。
2. 检查 flash JSON 的 `exit_code == 0`。
3. 根据当前 CLI surface、源码/配置或用户目标选择最小 probe 命令。
4. 运行 `.\agent_workbench\bin\agent_workbench.bat uart exec --reset-first --expect-ready --command <probe_command> --json`。
5. 检查 transcript 包含当前配置的 ready banner 和 prompt。
6. 如果目标需要数值、寄存器或运行态证据，自动检查/编辑 `agent_workbench/agent_workbench.yaml` 的 `monitor.items`，再使用 `monitor start --json`、触发目标行为、`monitor stop --json`、`monitor stats --json` 采集证据。

## 失败处理

- flash 失败：立刻报告 flash JSON、OpenOCD log 和 doctor report。
- 未见 ready banner：读 transcript 和 cli_diag，不要直接改源码。
- UART CLI 超时：读 `cli_diag.json` 和 `cli_transcript.log`。
- monitor 无数据：先确认 YAML、ELF 路径、symbol/address/value_type 和 debug 连接。
