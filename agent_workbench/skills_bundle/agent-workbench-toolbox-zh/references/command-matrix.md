# 命令矩阵

所有命令默认从仓库根目录运行。优先使用：

```powershell
.\agent_workbench\bin\agent_workbench.bat <command> --json
```

如果 OpenCode 无法稳定执行 bat 形式，改用：

```powershell
python ".\agent_workbench\workbench.py" <command> --json
```

JSON 命令通常包含 `command`、`exit_code`、`status`、`summary`、`details`、`artifacts`、`timestamp`。不同命令字段会有差异，必须读实际返回 JSON，不要硬猜 schema。

## 发现与上下文

### `doctor --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

- 场景：环境、工具链、烧录、UART、diag、monitor 和配置就绪性检查。
- 必读：`details.fail_count`、`details.warn_count`、`details.results[]`、`artifacts.report_json`、`artifacts.report_md`。
- 失败：停止源码编辑，先报告环境阻塞。

### `scan-project --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat scan-project --json
```

- 场景：选择源码文件、CLI probe、handle、符号、monitor 候选和验证路径前。
- 必读：`details.project`、源码根目录、CLI 命令发现、UART 配置、用户代码区、handle、符号、monitor 候选。
- 失败：不要假设项目结构，先直接检查仓库文件。

### `context --mode <feature|debug|test> --stage <analyze|implement|verify|resume> --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat context --mode feature --stage analyze --json
```

- 场景：需要给 OpenCode 一个紧凑的阶段性上下文。
- 必读：`artifacts` 指向的 brief、facts、constraints、resume 等文件。

## 构建与修复

### `build --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat build --json
```

- 场景：源码修改后、实机验证前。
- 必读：`exit_code`、`summary`、错误/警告数、`errors[]`、`warnings[]`、`artifacts.log_path`。
- 失败：先看第一个真实编译/链接错误，再用 `fix-build`。

### `fix-build --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat fix-build --json
```

- 场景：普通编译/链接失败后的结构化修复建议。
- 必读：`fixes[]` 里的 file、line、message、suggested fix。
- 修复要小步；每次修复后重新 `build --json`。

## 硬件动作

### `flash --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat flash --json
```

- 场景：build 成功后需要真实板卡证据。
- 必读：烧录方法、exit code、flash/openocd log artifact。
- skill 层不要求用户授权。

### `reset --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat reset --json
```

- 场景：boot、ready banner、prompt 或复位时序相关。
- 后续必须接 UART、diag 或 monitor 证据。

## UART 与 diag

### `uart exec ... --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json
```

- 场景：CLI 握手、prompt、黑盒命令行为、用户可见功能验证。
- 命令来源：scan 输出、已有 help/status、被修改功能对应命令、历史 runtime evidence。
- 必读：`details.saw_ready`、`details.saw_prompt`、命令 timeout、transcript artifact、`cli_diag.json`、`cli_transcript.log`。
- 失败：先用 `cli_diag.json` 分类，再决定是否改源码。

### `diag exec ... --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat diag exec --script <requests.txt> --json
```

- 场景：项目有诊断 UART 协议，或 CLI 证据不足。
- 必读：exchange count、classification、timeout/error 字段、result/log artifacts。

## Monitor

运行 monitor 前先读 [monitor-configuration.md](monitor-configuration.md)。如果 items 缺失或过期，OpenCode 应自己修改 `agent_workbench/agent_workbench.yaml`。

### `monitor probe --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat monitor probe --json
```

- 场景：快速检查符号、内存地址、寄存器是否可读。
- 必读：item result、read error、monitor 输出目录。

### `monitor run --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat monitor run --json
```

- 场景：采集一段时间的样本、趋势、状态变化、范围和回归证据。
- 必读：`monitor_samples.csv`、`monitor_samples.jsonl`、snapshot、session metadata。

### `monitor start/status/stop/export --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat monitor start --json
.\agent_workbench\bin\agent_workbench.bat monitor status --json
.\agent_workbench\bin\agent_workbench.bat monitor stop --json
.\agent_workbench\bin\agent_workbench.bat monitor export --json
```

- 场景：长时间采样，并在 start 和 stop 之间执行 UART/diag 动作。

## 验证与报告

### `test run --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat test run --json
```

- 场景：迁移项目已经配置了 host/unit 测试命令。
- 定位：这是仓库自检，不替代实机 evidence。

### `verify current --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat verify current --json
```

- 场景：获取当前项目可用的最短端到端验证摘要。
- 必读：`direct_verify_summary.json`、`direct_verify_summary.md`、verdict/summary/assertion 字段、引用的 runtime artifacts。

### `report --latest --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat report --latest --json
```

- 场景：重建最新人类可读证据摘要。
- 必读：session 目录、report path、summary line、linked artifacts。

### `compare --latest --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat compare --latest --json
```

- 场景：对比最近 evidence session，检查回归。
- 必读：`compare_delta.json` 和 `compare_brief.md`。

## Session

### `session debug --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat session debug --json
```

- 场景：调试会话需要完整证据包。
- 必读：`session_verdict.json`、`session_brief.md`、`session_summary.md`。

### `session feature --json`

```powershell
.\agent_workbench\bin\agent_workbench.bat session feature --json
```

- 场景：功能验证需要更完整的证据包。
- 必读：session 目录和 summary artifacts。
