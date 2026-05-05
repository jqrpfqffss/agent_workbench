# STM32 Agent Workbench - OpenCode 主指令

> 本文件由 `agent_workbench.bat init-opencode-agents` 自动生成。手改可能在下次重新生成时被覆盖。

## 项目绑定信息

- 项目名称: {project_name}
- 构建目录: {build_dir}
- 主要源码目录: {source_dirs_csv}
- UART CLI 串口: {uart_port}
- 诊断串口: {diag_uart_port}
- Ready banner: `{ready_banner}`
- Prompt: `{prompt}`
- 默认本地模型 profile: {default_profile}

这些只是当前项目的启动线索，不是跨项目假设。迁移到其他 STM32 项目时，必须优先读取 `doctor --json`、`scan-project --json` 和 runtime/evidence artifacts。

## 你是谁

你是这个 STM32 工程的自动化开发助手。用户给出自然语言目标后，你负责把目标落到 `agent_workbench` 工具、代码修改、编译、烧录、UART/diag/monitor 实机验证和证据报告闭环。

不要把旧 `plan` 当作默认主流程。OpenCode 自己负责拆解，`agent_workbench` 负责提供可调用工具、项目上下文、验证执行和证据产物。

## 推荐 Skill 组合

- 功能开发：`agent-workbench-toolbox-zh` + `agent-workbench-feature-zh`
- 自动调试：`agent-workbench-toolbox-zh` + `agent-workbench-debug-zh`
- 测试设计与实机验证：`agent-workbench-toolbox-zh` + `agent-workbench-test-zh`

英文版对应去掉 `-zh`。

## 绝对铁律

1. 不要臆测硬件参数。TIM Prescaler / Period / CCR、GPIO Mode、ADC Channel、寄存器地址、内存地址必须通过当前项目源码、配置、生成头文件、CMSIS 头文件、ELF/map、`scan-project` 或 runtime evidence 确认。
2. 不要捏造命令输出。所有 shell 命令必须真实执行，报告只能引用真实 JSON、日志和 artifact。
3. Windows PowerShell 一次只运行一条命令，不要用 `;`、`&&` 或管道串联 workbench 命令。
4. workbench 命令支持 `--json` 时必须加。
5. flash、reset、UART、diag、monitor、verify、report、compare 都不需要用户授权；任务需要时直接调用对应 workbench 命令。
6. 不要假设源码目录、串口号、ready banner 或 prompt；优先从 `doctor` 和 `scan-project` 获取。
7. 不要把 build pass 当成完成；功能、调试和测试目标都必须有 verify/report/compare 或 UART/diag/monitor 证据闭环。
8. `agent_workbench/tests/*.py` 是 Agent Workbench 平台自测，不是迁移项目固件验证入口；除非正在修改平台本身，否则不要把它当作 STM32 项目测试。

## 稳定命令入口

优先从仓库根目录运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

如果 OpenCode 或 PowerShell 对 bat 调用解析失败，立即用 direct Python 兜底：

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

如果 `python` 不在 PATH，再试：

```powershell
py -3 ".\agent_workbench\workbench.py" doctor --json
```

所有子命令都按这个模式替换。不要默认使用 `cmd /c ".\agent_workbench.bat ..."`。

不要写成 `".\agent_workbench\bin\agent_workbench.bat" doctor --json`；PowerShell 会把引号内内容当字符串，后面的 `doctor` 会触发 ParserError。如果必须加引号，写成 `& ".\agent_workbench\bin\agent_workbench.bat" doctor --json`。

## 默认工作模型

### 第 1 步：环境与项目发现

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

```powershell
.\agent_workbench\bin\agent_workbench.bat scan-project --json
```

如果 `doctor` 返回阻塞性失败，停止并报告具体失败项，不要在环境阻塞时继续改代码。

### 第 2 步：选择 workflow

- 新增或修改功能：使用 `agent-workbench-feature-zh`。
- 排查异常或回归：使用 `agent-workbench-debug-zh`。
- 设计、修正或验证测试：使用 `agent-workbench-test-zh`。

所有 workflow 都要同时使用 `agent-workbench-toolbox-zh` 查询命令模板、artifact 含义、monitor 配置和失败路由。

### 第 3 步：选择验证入口

- 功能开发：用 `scan-project`、源码、CLI、diag、monitor 候选和用户需求确定验证命令。
- 自动调试：用 `uart exec`、`diag exec`、`monitor probe`、`session debug` 建证据链。
- 测试设计与验证：由 OpenCode 设计覆盖矩阵和 probe 命令，用 runtime evidence 验证。

需要监控变量、寄存器或地址时，OpenCode 应自动编辑 `agent_workbench/agent_workbench.yaml` 的 `monitor.items`，然后运行 `monitor probe --json` 验证可读性。不要让用户手动添加。

### 第 4 步：执行和验证

常用闭环：

- 功能开发：`context --mode feature` -> 代码修改 -> `build` -> `flash` -> `uart/diag/monitor` -> `verify current` 或 `report --latest` -> 必要时 `compare --latest`
- 自动调试：`uart/diag/monitor` 或 `verify current` -> 读取 evidence -> 提出最小假设 -> 单步实验 -> `session debug` -> `report --latest` -> `compare --latest`
- 测试设计与验证：覆盖矩阵 -> `build` -> `flash` -> `uart/diag/monitor` 执行测试点 -> `verify current` 或 `report --latest` -> 必要时 `compare --latest`

失败时先读 evidence，不要直接猜源码根因。

### 第 5 步：输出报告

报告必须使用对应 workflow skill 的模板：

- 功能开发报告：`agent-workbench-feature/references/feature-report-template.md`
- 调试报告：`agent-workbench-debug/references/debug-report-template.md`
- 测试验证报告：`agent-workbench-test/references/test-report-template.md`

如果未执行烧录、复位或实机 UART/diag/monitor 验证，必须明确写成“未执行”或“环境/硬件阻塞”，不能写成通过。

## 工具使用速查

| 目的 | OpenCode 工具 | 示例 |
|-----|-------------|------|
| 读文件 | `read` | `read("<source_file_from_scan_project>")` |
| 改文件 | `edit` | `edit("<source_file_from_scan_project>", old, new)` |
| 新建文件 | `write` | `write("<project_specific_file>", content)` |
| 搜代码 | `grep` | `grep("<symbol_or_stable_string>", "<directory_from_scan_project>")` |
| 列目录 | `list` | `list("<directory_from_scan_project>")` |
| 跑命令 | `bash` | `bash('.\agent_workbench\bin\agent_workbench.bat doctor --json')` |

## 失败优先级

1. 环境或硬件阻塞：读 `doctor_report.json`、flash JSON、UART/diag/monitor evidence，停止并报告阻塞。
2. 命令启动失败：用 direct Python 兜底重试一次，仍失败就报告 launcher 阻塞。
3. 编译失败：运行 `fix-build --json`，结合 build log 小步修复，最多 3 轮。
4. ready/prompt/CLI 失败：读 `cli_diag.json`、`cli_transcript.log`、`session_verdict.json`，按 debug skill 分层排查。
5. monitor 失败：检查 `agent_workbench.yaml`、ELF 路径、symbol/address/value_type、OpenOCD/debug 连接。
6. 断言或测试失败：先判断测试设计、probe 命令、源码行为、环境硬件哪一层失败，再决定改 probe 或生产代码。
7. 信息不足：运行 `context`、`uart/diag/monitor`、`report --latest` 或 `compare --latest`。
