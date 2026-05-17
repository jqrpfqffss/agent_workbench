# OpenCode / Codex 使用 Agent Workbench 的 Skill 指南

本文说明在 OpenCode、Codex 或类似 agent 前端中，如何围绕当前精简版 `agent_workbench` 使用技能包和提示词。重点是让 agent 稳定调用现有命令、读取真实 evidence，并避免继续使用已删除的旧命令体系。

## 1. 当前原则

`agent_workbench` 当前只支持 README 中列出的命令。agent 不应调用历史文档或旧 skill reference 中的以下入口：

- `scan-project`
- `context`
- `plan`
- `session`
- `verify current`
- `report`
- `compare`
- `integration`
- `test run`
- `monitor probe`
- `monitor run`
- `monitor status`
- `monitor export`
- `init-vscode`

如果某个 skill 文本仍然建议使用这些命令，应以当前 `agent_workbench/README.md`、`workbench.py` 和本文为准。

## 2. Skill 安装

仓库中仍保留 skill bundle：

```text
agent_workbench/skills_bundle/
```

常见安装位置：

```text
%CODEX_HOME%\skills\
```

如果未设置 `CODEX_HOME`：

```text
%USERPROFILE%\.codex\skills\
```

可安装的目录包括：

```text
agent-workbench-toolbox-zh
agent-workbench-feature-zh
agent-workbench-debug-zh
agent-workbench-test-zh
agent-workbench-dt-test-zh
agent-workbench-toolbox
agent-workbench-feature
agent-workbench-debug
agent-workbench-test
```

安装后重启 OpenCode/Codex 会话。使用时可以显式提到 skill 名称，例如：

```text
使用 $agent-workbench-toolbox-zh，先按当前 README 支持的命令检查这个 STM32 项目。
```

## 3. 推荐开场提示词

第一次进入项目时，建议这样提示：

```text
使用 $agent-workbench-toolbox-zh。
当前项目使用精简版 agent_workbench，只允许调用 README 中列出的命令。
请先从仓库根目录运行：
.\agent_workbench\bin\agent_workbench.bat doctor --json
然后根据真实 JSON 总结 build、flash、UART、diag、monitor、remote-dt 的可用性。
不要使用 scan-project、context、plan、session、verify、report、compare、integration、test run 或 monitor probe/run。
不要假设串口号、ready banner、prompt、ELF 路径、monitor item、寄存器地址或内存地址。
```

agent 应先运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

bat 启动失败时才兜底：

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

仍失败再试：

```powershell
py -3 ".\agent_workbench\workbench.py" doctor --json
```

## 4. Agent 可用命令手册

### 4.1 发现与环境

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

必须读取：

- `exit_code`
- `status`
- `details.fail_count`
- `details.warn_count`
- `details.results[]`
- `artifacts.report_json`
- `artifacts.report_md`

如果 fail_count 大于 0，agent 应停止后续源码修改，先报告阻塞项。

### 4.2 构建与修复

```powershell
.\agent_workbench\bin\agent_workbench.bat build --json
```

失败后：

```powershell
.\agent_workbench\bin\agent_workbench.bat fix-build --json
```

agent 应读取：

- `runtime/build.log`
- `errors[]`
- `warnings[]`
- `suggested_fixes`

`fix-build` 不是自动修复器，它只把日志转成结构化建议。agent 仍然要结合源码做最小修改，并重新运行 `build --json`。

### 4.3 烧录与复位

```powershell
.\agent_workbench\bin\agent_workbench.bat flash --json
.\agent_workbench\bin\agent_workbench.bat reset --json
```

在本项目规则下，flash 和 reset 不需要额外向用户要授权。执行后必须读取 JSON 和日志产物。

### 4.4 UART CLI

```powershell
.\agent_workbench\bin\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json
```

如果目标固件没有 `help/status`，agent 应根据当前源码、README、用户要求或已有 runtime evidence 选择真实命令。

必须读取：

- `details.saw_ready`
- `details.saw_prompt`
- `details.timeout_commands`
- `transcript`
- `artifacts.transcript_path`
- `artifacts.diag_path`

失败时必须同时读：

- `agent_workbench/runtime/cli_transcript.log`
- `agent_workbench/runtime/cli_diag.json`
- `agent_workbench/runtime/uart_exec_reset.log`，如果用了 `--reset-first`

### 4.5 Diag

```powershell
.\agent_workbench\bin\agent_workbench.bat diag exec --json
```

或：

```powershell
.\agent_workbench\bin\agent_workbench.bat diag exec --hex "68 65 6C 70 0D 0A" --json
```

agent 不得把示例 hex 帧当成真实协议。真实帧必须来自目标项目协议、源码、用户说明或运行证据。

### 4.6 Monitor

当前公开 monitor 命令是后台采样模型：

```powershell
.\agent_workbench\bin\agent_workbench.bat monitor start --json
.\agent_workbench\bin\agent_workbench.bat monitor start --reset-first --json
.\agent_workbench\bin\agent_workbench.bat monitor stop --json
.\agent_workbench\bin\agent_workbench.bat monitor stats --json
```

典型使用方式：

1. 根据当前证据编辑 `agent_workbench/agent_workbench.yaml` 中的 `monitor.items`。
2. 运行 `doctor --json`，确认 `monitor_symbol_image` 和 `monitor_items` 没有阻塞。
3. 运行 `monitor start --reset-first --json`。
4. 在采样期间运行 `uart exec` 或 `diag exec` 触发行为。
5. 运行 `monitor stop --json`。
6. 运行 `monitor stats --json`。
7. 分析 `monitor_samples.csv`、`monitor_samples_wide.csv`、`monitor_samples.jsonl` 和 `monitor_session.jsonl`。

agent 可以自动编辑 monitor 配置，但必须遵守：

- 符号来自 ELF、map 或当前源码。
- 地址来自 CMSIS/设备头文件、map、链接脚本、参考手册或用户明确输入。
- 不复制示例地址。
- 高频采样尽量避免 CPU register item。

### 4.7 Remote DT

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt build --json
.\agent_workbench\bin\agent_workbench.bat remote-dt execute --json
.\agent_workbench\bin\agent_workbench.bat remote-dt coverage --json
.\agent_workbench\bin\agent_workbench.bat remote-dt pipeline --json
.\agent_workbench\bin\agent_workbench.bat remote-dt pull-logs --json
```

agent 必须读取：

- `agent_workbench/runtime/remote_dt/dt_remote_result.json`
- `agent_workbench/runtime/remote_dt/dt_remote_summary.md`
- `agent_workbench/runtime/remote_dt/logs/dt_build.log`
- `agent_workbench/runtime/remote_dt/logs/dt_execute.log`
- `agent_workbench/runtime/remote_dt/logs/dt_coverage.log`

remote-dt 失败时先报告失败阶段，再引用对应日志。

## 5. 功能开发提示词

推荐组合：

```text
$agent-workbench-toolbox-zh + $agent-workbench-feature-zh
```

推荐提示：

```text
使用 $agent-workbench-toolbox-zh 和 $agent-workbench-feature-zh。
我要在当前 STM32 项目中实现 <功能描述>。
本项目使用精简版 agent_workbench，只能调用 README 中支持的命令。
请先运行 doctor --json；修改前读取必要源码和配置；修改后运行 build --json。
如果需要硬件闭环，请运行 flash/reset，并用 uart exec、diag exec 或 monitor start/stop/stats 采集证据。
不要把 build pass 当作完成。最终报告列出实际执行命令、exit_code 和 artifact 路径。
```

功能开发完成标准：

- `doctor --json` 没有阻塞性 fail。
- `build --json` 成功，或失败被明确报告。
- 需要硬件时有 flash/reset/UART/diag/monitor 中至少一种真实 evidence。
- 报告引用真实 artifact，而不是口头判断。

## 6. 自动调试提示词

推荐组合：

```text
$agent-workbench-toolbox-zh + $agent-workbench-debug-zh
```

推荐提示：

```text
使用 $agent-workbench-toolbox-zh 和 $agent-workbench-debug-zh。
当前 STM32 项目出现 <故障现象>。
请按 evidence-first 方法排查：doctor -> build/fix-build -> flash/reset -> uart exec/diag exec -> monitor start/stop/stats。
不要使用旧命令，不要先猜源码根因，不要捏造硬件输出。
每次只验证一个假设，最后输出根因、证据、已执行命令、exit_code 和 artifact。
```

调试分层：

| 层级 | 命令或证据 |
|---|---|
| 环境配置 | `doctor --json`、`doctor_report.json` |
| 构建 | `build --json`、`build.log`、`fix-build --json` |
| 烧录复位 | `flash.log`、`reset.log`、`uart_exec_reset.log` |
| UART | `cli_transcript.log`、`cli_diag.json` |
| diag | `diag_exchange.log`、`diag_exec_result.json` |
| monitor | `monitor_session.jsonl`、`monitor_samples.csv/jsonl` |
| remote-dt | `dt_remote_result.json`、`dt_remote_summary.md`、`logs/dt_*.log` |

## 7. 测试设计与实机验证提示词

推荐组合：

```text
$agent-workbench-toolbox-zh + $agent-workbench-test-zh
```

推荐提示：

```text
使用 $agent-workbench-toolbox-zh 和 $agent-workbench-test-zh。
请为当前 STM32 项目的 <功能/模块> 设计测试覆盖矩阵，并在当前 workbench 支持的命令范围内执行验证。
覆盖正常路径、边界值、非法输入、reset 后行为、状态迁移和回归风险。
可用验证面包括 build、flash、reset、uart exec、diag exec、monitor start/stop/stats、remote-dt。
不要把 agent_workbench/tests/*.py 当作固件测试。最终报告必须引用真实 artifact。
```

测试矩阵至少包含：

- 测试目标
- 输入或触发动作
- 期望输出或状态
- 观测方式：UART、diag、monitor、remote-dt 或 build
- 实际结果
- artifact 路径
- 是否通过

## 7.1 DT 用例与 Remote DT 提示词

推荐 skill：

```text
$agent-workbench-dt-test-zh
```

推荐提示：

```text
使用 $agent-workbench-dt-test-zh。
请为当前 STM32 项目的 <模块/功能> 编写 DT 测试用例，并接入 remote-dt 执行入口。
只使用 remote-dt build/execute/coverage/pipeline/pull-logs 五条命令，且必须加 --json。
不要把 agent_workbench/tests/*.py 当作固件测试。
如果 remote_dt 未启用或远端代码同步无法确认，请继续完成用例设计/本地改动，但把远端验证标为 blocked。
最终报告列出实际 remote-dt 命令、exit_code、dt_remote_result/summary/log/coverage artifact。
```

DT 用例报告至少包含：

- case id、目标行为、触发方式、观测面和期望结果
- remote-dt 阶段状态和失败阶段
- `dt_remote_result.json`、`dt_remote_summary.md`、`logs/dt_*.log`、`coverage/` 路径
- pass/fail/blocked 结论和未覆盖风险

## 8. 判断 agent 是否用对了 workbench

本节用于通用本地 workflow。使用 `$agent-workbench-dt-test-zh` 时，以 7.1 的五条 remote-dt 命令边界为准。

正确表现：

- 第一条命令是 `doctor --json`。
- bat 失败时才用 direct Python 兜底。
- 只调用当前 README 支持的命令。
- 修改代码后运行 `build --json`。
- 需要硬件证据时主动运行 flash、reset、UART、diag 或 monitor。
- 失败时读取 artifact，而不是只看摘要。
- 报告中列出命令、exit_code 和 artifact 路径。

错误表现：

- 使用旧命令。
- 只跑构建就宣布功能完成。
- 没有串口或 monitor 证据却声称实机通过。
- 复制示例串口、prompt、寄存器地址或 monitor item。
- 把 `agent_workbench/tests/*.py` 当作目标固件测试。
- 只给建议，不执行当前可执行的验证命令。

如果 agent 跑偏，可以直接打断：

```text
停止。请按当前 agent_workbench/README.md 重新执行。
本项目只允许使用 doctor、build、fix-build、flash、reset、uart exec、diag exec、monitor start/stop/stats 和 remote-dt 相关命令。
请先运行 doctor --json，然后用真实 JSON 和 artifact 建立证据链。
```

## 9. 报告模板

最终报告建议固定包含：

```text
结论：
- pass/fail/blocked

实际执行：
- <command> -> exit_code=<n>, artifact=<path>

关键证据：
- doctor: <fail/warn 摘要>
- build: <errors/warnings 摘要>
- hardware: <flash/reset/UART/diag/monitor 证据>
- remote-dt: <阶段结果，如适用>

改动：
- <文件和要点>

未执行：
- <未执行的硬件或远程验证及原因>
```

这能让后续维护者快速判断：当前回答是基于真实证据，还是只是源码层面的推断。
