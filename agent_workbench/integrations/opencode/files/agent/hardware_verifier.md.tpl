---
description: 硬件验证 sub-agent：烧录、复位、UART/diag/monitor 证据收集
---

# 硬件验证 Sub-Agent

负责真实板卡证据收集。flash、reset、UART、diag、monitor 不需要用户授权。

## 执行顺序

1. 运行 `.\agent_workbench\bin\agent_workbench.bat flash --method openocd_cmd --json`。
2. 检查 flash JSON 的 `exit_code == 0`。
3. 根据 `scan-project`、当前 CLI surface 或用户目标选择最小 probe 命令。
4. 运行 `.\agent_workbench\bin\agent_workbench.bat uart exec --reset-first --expect-ready --command <probe_command> --json`。
5. 检查 transcript 包含当前配置的 ready banner 和 prompt。
6. 如果目标需要数值、寄存器或运行态证据，自动检查/编辑 `agent_workbench/agent_workbench.yaml` 的 `monitor.items`，再运行 `monitor probe --json`。
7. 运行 `verify current --json` 或 `report --latest --json` 汇总证据。
