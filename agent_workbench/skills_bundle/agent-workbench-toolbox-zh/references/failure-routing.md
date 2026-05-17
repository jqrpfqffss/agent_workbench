# 失败路由

失败后先分层，再修改。不要从第一个症状直接跳到源码重构。

## 环境或配置失败

- 证据：`doctor --json`、`doctor_report.json/md`。
- 下一步：报告缺失工具、路径、端口、OpenOCD、Python 或 YAML 配置问题。
- 不要：继续改固件源码。

## 命令启动失败

- 证据：shell stderr、exit code。
- 下一步：从 batch 入口切换到 direct Python 兜底，见 `command-execution.md`。
- 不要：把 launcher 失败误判成 workbench 功能失败。

## Build 失败

- 证据：命令 JSON、`build.log`、`fix-build --json` 的 `suggested_fixes[]`。
- 下一步：按第一个真实 compiler/linker error 小步修复，最多 3 轮。

## Flash/Reset 失败

- 证据：flash/reset JSON、OpenOCD log、`doctor_report.json`。
- 下一步：检查 method、probe、target power、路径和 ELF 是否来自当前 build。

## Ready 缺失

- 证据：UART JSON、`tmp/uart_exec_result.json`、`cli_transcript.log`、reset/flash log。
- 下一步：区分固件未启动、波特率/端口错误、reset 时序、ready 字符串变化、UART 初始化失败。

## Prompt 缺失

- 证据：transcript、UART result。
- 下一步：区分 parser 没进命令循环、prompt 字符串变化、命令阻塞、UART TX 问题。

## Parser 或命令行为失败

- 证据：UART transcript、UART result、对应 CLI handler 源码。
- 下一步：用最小 CLI probe 复现；内部状态不清楚时增加 monitor item。

## Diag 失败

- 证据：`diag_exec_result.json`、`diag_exchange.log`。
- 下一步：确认 diag_uart 配置、请求格式、超时、协议源码和是否与 CLI 共用串口。

## Monitor 无数据或读失败

- 证据：monitor start/stats JSON、`monitor_live/monitor.log`、`monitor_session.jsonl`、`agent_workbench.yaml`。
- 下一步：确认 `monitor.enabled`、ELF 路径、symbol、address、value_type、OpenOCD/debug 连接和 target run state。

## 测试或回归失败

- 证据：UART/diag/monitor artifacts 和源码行为契约。
- 下一步：判断是期望过时、probe 不足、行为真实回归，还是环境阻塞。
