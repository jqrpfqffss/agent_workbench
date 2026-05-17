# 命令矩阵

所有命令默认从仓库根目录运行。优先使用：

```powershell
./agent_workbench/bin/agent_workbench.bat <command> --json
```

batch 启动失败时，按 [command-execution.md](command-execution.md) 切换到 direct Python 入口。

JSON 通常包含 `command`、`exit_code`、`status`、`summary`、`details`、`artifacts`、`timestamp`，但字段可能因命令不同而变化。必须读实际返回 JSON，不要硬猜 schema。

## 发现

### `doctor --json`

```powershell
./agent_workbench/bin/agent_workbench.bat doctor --json
```

- 场景：环境、工具链、ELF、flash、UART、diag、monitor 和配置就绪性检查。
- 必读：`exit_code`、`status`、`summary`、`details.results[]`、`artifacts.report_json`、`artifacts.report_md`。
- 失败：停止源码修改，先报告阻塞项。

## 构建

### `build --json`

```powershell
./agent_workbench/bin/agent_workbench.bat build --json
```

- 场景：源码或配置修改后，flash/实机验证前。
- 必读：`exit_code`、`status`、`summary`、`artifacts.log_path` 或 `agent_workbench/runtime/build.log`。
- 失败：先读第一个真实 compiler/linker error，再运行 `fix-build --json`。

### `fix-build --json`

```powershell
./agent_workbench/bin/agent_workbench.bat fix-build --json
```

- 场景：普通编译/链接失败后的结构化建议。
- 必读：`suggested_fixes[]`、`artifacts.log_path`。
- 规则：小步修复；每次修复后重新 `build --json`，最多 3 轮。

## 烧录与复位

### `flash --json`

```powershell
./agent_workbench/bin/agent_workbench.bat flash --json
```

- 场景：build 成功后需要真实板卡证据。
- 必读：`exit_code`、`summary`、flash/OpenOCD log artifact。
- 规则：skill 层不要求用户授权。

### `reset --json`

```powershell
./agent_workbench/bin/agent_workbench.bat reset --json
```

- 场景：启动、ready banner、prompt、复位恢复或复位时序相关。
- 后续：必须接 UART、diag 或 monitor evidence，不能只凭 reset 通过下结论。

## UART 与 diag

### `uart exec --reset-first --json`

```powershell
./agent_workbench/bin/agent_workbench.bat uart exec --reset-first --command help --command status --json
```

- 场景：CLI 命令、黑盒 transcript、用户可见行为验证。
- 命令来源：当前配置的 `uart.probe_commands`、help/status 输出、用户需求或当前源码。
- 必读：JSON 中 ready/prompt/timeout 字段、`cli_transcript.log`、`agent_workbench/runtime/tmp/uart_exec_result.json`。

### `uart exec --reset-first --expect-ready --json`

```powershell
./agent_workbench/bin/agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json
```

- 场景：严格验证 ready banner 和 prompt。
- 失败：先读 transcript 和 UART result，再判断是端口占用、ready 缺失、prompt 缺失、命令 timeout，还是固件逻辑问题。

### `diag exec --json`

```powershell
./agent_workbench/bin/agent_workbench.bat diag exec --json
```

```powershell
./agent_workbench/bin/agent_workbench.bat diag exec --hex "68 65 6C 70 0D 0A" --json
```

- 场景：项目有诊断串口/原始报文协议，或 UART CLI 证据不足。
- 必读：`diag_exec_result.json`、`diag_exchange.log`、timeout/error/exchange 字段。

## Monitor

运行 monitor 前先读 [monitor-configuration.md](monitor-configuration.md)。如果 items 缺失或过期，Codex 应自己修改 `agent_workbench/agent_workbench.yaml`。

### `monitor start --json`

```powershell
./agent_workbench/bin/agent_workbench.bat monitor start --json
```

- 场景：开始采集变量、寄存器、内存地址、计数器或趋势。
- 必读：`summary` 中的 pid、out、log；`agent_workbench/runtime/monitor_live/`。

### `monitor start --reset-first --json`

```powershell
./agent_workbench/bin/agent_workbench.bat monitor start --reset-first --json
```

- 场景：需要从复位后开始采样启动状态或趋势。

### `monitor stop --json`

```powershell
./agent_workbench/bin/agent_workbench.bat monitor stop --json
```

- 场景：停止后台采样。不要在最终回复前留下本任务启动的 monitor 后台进程。

### `monitor stats --json`

```powershell
./agent_workbench/bin/agent_workbench.bat monitor stats --json
```

- 场景：汇总 `monitor_samples.csv`。
- 必读：sample count、实际采样频率、每个 item 的 last/min/max/error 统计。
