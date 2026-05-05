# 产物地图

artifact 是事实来源。不要凭记忆总结一次运行。

## 最高优先级证据

### `session_verdict.json`

- 最适合最终 pass/fail、blocked 状态和根因线索。
- `session debug` 或 `session feature` 后，最终结论前必须读。

### `direct_verify_summary.json` / `direct_verify_summary.md`

- 最适合 `verify current`。
- 读取 verdict、steps、assertions、blocked reason 和 linked artifacts。

### `cli_diag.json`

- 最适合 UART/CLI 失败分类。
- 修改 parser、命令 handler、UART init 或 prompt 逻辑前先读。

### `cli_transcript.log`

- 最适合确认串口真实收发。
- 用来确认 ready banner、prompt、command echo、command response 和 timeout 边界。

### `monitor_samples.csv` / `monitor_samples.jsonl`

- 最适合运行态变量、计数器、状态迁移、寄存器读取和趋势。
- 缺样本或数值陈旧是需要排查的证据，不是固件行为的证明。

### `compare_delta.json` / `compare_brief.md`

- 最适合最近 session 之间的回归判断。
- 修复后用它证明失败改善，且没有明显旧证据回退。

### `doctor_report.json` / `doctor_report.md`

- 最适合环境和配置阻塞。
- 命令因 setup、toolchain、port、flash 或 monitor 可用性失败时，改源码前先读。

## 常见 runtime 输出

- `build.log`：编译/链接事实来源。
- `flash.log` 或 OpenOCD logs：烧录/复位事实来源。
- `session_brief.md`：面向用户的简要证据摘要。
- `session_summary.md`：更完整的 session 叙述和 artifact 链接。
- `monitor_snapshot.csv`：快速查看最新 monitor 值。
- `monitor_session.jsonl`：monitor session 事件和元数据。
- `report.md` 或 latest report artifact：生成的证据报告。

## 按场景读取顺序

- build 失败：命令 JSON -> `build.log` -> `fix-build` 建议。
- flash 失败：命令 JSON -> flash/openocd log -> `doctor_report.json`。
- ready/prompt 缺失：UART JSON -> `cli_diag.json` -> `cli_transcript.log` -> reset/flash evidence。
- CLI 行为不符：transcript -> `cli_diag.json` -> source handler -> 内部状态不清楚时加 monitor items。
- monitor 失败：monitor JSON -> monitor 输出目录 -> `doctor_report.json` -> YAML monitor config -> OpenOCD/debug state。
- 回归：`compare_delta.json` -> 前后 session summary -> 聚焦 UART/monitor 复现。

## 报告规则

给用户报告时，必须包含精确 artifact 路径，以及支撑结论的字段或关键行。
