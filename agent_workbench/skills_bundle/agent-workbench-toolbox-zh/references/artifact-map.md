# 产物地图

artifact 是事实来源。不要凭记忆总结一次运行，也不要引用未执行命令的产物。

## 常见 runtime 输出

- `agent_workbench/runtime/doctor_report.json` / `.md`：环境、配置、工具链、端口、flash、UART、diag、monitor readiness。
- `agent_workbench/runtime/build.log`：CMake/编译/链接事实来源。
- `agent_workbench/runtime/flash.log`：烧录事实来源。
- `agent_workbench/runtime/reset.log`：复位事实来源。
- `agent_workbench/runtime/uart_exec_reset.log`：`uart exec --reset-first` 触发的 reset log。
- `agent_workbench/runtime/cli_transcript.log`：UART 真实收发、ready、prompt、命令响应和 timeout 边界。
- `agent_workbench/runtime/tmp/uart_exec_result.json`：UART exec 的结构化结果。
- `agent_workbench/runtime/diag_exec_result.json`：diag exec 的结构化结果。
- `agent_workbench/runtime/diag_exchange.log`：diag 原始请求/响应记录。
- `agent_workbench/runtime/monitor_live/monitor_samples.csv`：monitor 长表样本。
- `agent_workbench/runtime/monitor_live/monitor_samples_wide.csv`：monitor 宽表样本。
- `agent_workbench/runtime/monitor_live/monitor_samples.jsonl`：monitor JSONL 样本。
- `agent_workbench/runtime/monitor_live/monitor_snapshot.csv`：monitor 最新快照。
- `agent_workbench/runtime/monitor_live/monitor_session.jsonl`：monitor 事件和元数据。
- `agent_workbench/runtime/monitor_live/monitor.log`：monitor 后台进程日志。
- `agent_workbench/runtime/openocd_live/openocd.log`：OpenOCD live log。

## 按场景读取顺序

- `doctor` 失败：命令 JSON -> `doctor_report.json` -> `doctor_report.md`。
- build 失败：命令 JSON -> `build.log` -> `fix-build --json` 的 `suggested_fixes[]`。
- flash/reset 失败：命令 JSON -> `flash.log`/`reset.log` -> `doctor_report.json`。
- ready/prompt 缺失：UART JSON -> `tmp/uart_exec_result.json` -> `cli_transcript.log` -> reset/flash evidence。
- CLI 行为不符：transcript -> UART result -> 对应 CLI handler 源码 -> 必要时 monitor evidence。
- diag 失败：命令 JSON -> `diag_exec_result.json` -> `diag_exchange.log` -> diag 配置/协议源码。
- monitor 失败：命令 JSON -> `monitor_live/monitor.log` -> `monitor_session.jsonl` -> `doctor_report.json` -> YAML monitor config。

## 报告规则

给用户报告时，必须包含精确 artifact 路径，以及支撑结论的字段或关键行。没有 artifact 的结论只能写成推断，不能写成验证事实。
