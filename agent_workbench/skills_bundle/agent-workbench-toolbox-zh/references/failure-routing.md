# 失败路由

失败后先分层，再修改。不要从第一个症状直接跳到源码重构。

## 环境或配置失败

- 证据：`doctor --json`、`doctor_report.json/md`。
- 下一步：报告缺失工具、路径、端口、OpenOCD、Python 或 YAML 配置问题。
- 不要：继续改固件源码。

## 命令启动失败

- 证据：shell stderr、exit code。
- 下一步：从 bat 入口切换到 direct Python 兜底，见 `opencode-command-execution.md`。
- 不要：把 launcher 失败误判成 workbench 功能失败。

## Build 失败

- 证据：命令 JSON、`build.log`、`fix-build --json`。
- 下一步：按第一个真实 compiler/linker error 小步修复。

## Flash/Reset 失败

- 证据：flash/reset JSON、OpenOCD log、`doctor_report.json`。
- 下一步：检查 method、probe、target power、路径和 ELF 是否当前 build。

## Ready 缺失

- 证据：UART JSON、`cli_diag.json`、`cli_transcript.log`、reset/flash log。
- 下一步：区分固件未启动、波特率/端口错误、reset 时序、ready 字符串不稳定。

## Prompt 缺失

- 证据：transcript、`cli_diag.json`。
- 下一步：区分 parser 没进命令循环、prompt 字符串变化、命令阻塞、UART TX 问题。

## Parser 或命令行为失败

- 证据：`cli_diag.json`、transcript、对应 CLI handler 源码。
- 下一步：用最小 CLI probe 复现；内部状态不清楚时增加 monitor item。

## Monitor 无数据或读失败

- 证据：monitor JSON、monitor 输出目录、`doctor_report.json`、`agent_workbench.yaml`。
- 下一步：确认 `monitor.enabled`、ELF 路径、symbol、address、value_type、OpenOCD/debug 连接和 target run state。

## Assertion 或回归失败

- 证据：`direct_verify_summary.json`、transcript、monitor samples、`compare_delta.json`。
- 下一步：判断是期望过时、行为真实回归、证据面不足，还是环境阻塞。
