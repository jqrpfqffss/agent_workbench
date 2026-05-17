# 调试实验 Playbook

## 实验模板

```text
实验目标: <要区分的假设>
命令: <单条 workbench 命令>
观察字段: <JSON 字段或 artifact>
通过说明: <看到什么意味着假设成立>
失败说明: <看到什么意味着假设被否定>
下一步: <根据结果走哪条路由>
```

## 环境实验

- 目标：确认工具链、配置、串口、烧录器、monitor、remote-dt 可用性。
- 命令：`doctor --json`
- 失败：停止，不改源码。

## 构建实验

- 目标：确认当前源码能生成固件。
- 命令：`build --json`
- 失败：`fix-build --json`，然后小步修复。

## 烧录实验

- 目标：确认固件进入目标板。
- 命令：`flash --json`
- 注意：不需要用户授权；任务需要时直接执行。

## UART 握手实验

- 目标：确认 ready/prompt 和基本命令。
- 命令：`uart exec --reset-first --expect-ready --command <probe> --json`
- 失败：读 `tmp/uart_exec_result.json` 和 `cli_transcript.log`。

## Diag 实验

- 目标：确认诊断请求/响应是否符合当前协议。
- 命令：`diag exec --json` 或 `diag exec --hex "<bytes>" --json`
- 失败：读 `diag_exec_result.json` 和 `diag_exchange.log`。

## 运行态实验

- 目标：确认变量、状态机或外设状态。
- 命令：`monitor start --json` -> 触发行为 -> `monitor stop --json` -> `monitor stats --json`
- 失败：确认符号、ELF、目标运行、OpenOCD 和 monitor 配置。

## Remote DT 实验

- 目标：确认远端构建、执行或覆盖率链路。
- 命令：`remote-dt pipeline --json` 或更窄的 `remote-dt build/execute/coverage --json`
- 关注：`dt_remote_result.json`、`dt_remote_summary.md`、`logs/dt_*.log`。
