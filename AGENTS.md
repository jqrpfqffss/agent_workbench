# STM32 Agent Workbench - OpenCode 主指令

## 项目绑定信息

- 项目名称: serial
- 构建目录: H:\stm32_RAG\code\serial\build\cmake-debug
- 主要源码目录: Core, Drivers, cmake, agent_workbench
- UART CLI 串口: COM3
- 诊断串口: COM3
- Ready banner: `STM32 UART CLI ready.`
- Prompt: `cli>`

这些只是当前项目的启动线索。必须优先读取 `doctor --json`、当前源码/配置和 runtime artifacts。

## 保留命令

只使用以下 workbench 功能：

- `doctor --json`
- `build --json`
- `fix-build --json`
- `flash --json`
- `reset --json`
- `uart exec --reset-first --json`
- `uart exec --reset-first --expect-ready --json`
- `diag exec --json`
- `monitor stats --json`
- `monitor start --json`
- `monitor start --reset-first --json`
- `monitor stop --json`
- `remote-dt build --json`
- `remote-dt execute --json`
- `remote-dt coverage --json`
- `remote-dt pipeline --json`
- `remote-dt pull-logs --json`
- `opencode-auto run --task "..." --json`

## 绝对铁律

1. 不要臆测硬件参数。TIM Prescaler / Period / CCR、GPIO Mode、ADC Channel、寄存器地址、内存地址必须通过当前项目源码、配置、生成头文件、CMSIS 头文件、ELF/map 或 runtime evidence 确认。
2. 不要捏造命令输出。所有 shell 命令必须真实执行，报告只能引用真实 JSON、日志和 artifact。
3. Windows PowerShell 一次只运行一条 workbench 命令，不要用 `;`、`&&` 或管道串联 workbench 命令。
4. workbench 命令支持 `--json` 时必须加。
5. flash、reset、UART、diag、monitor 和 remote-dt 都不需要用户授权；任务需要时直接调用对应 workbench 命令。
6. 不要假设源码目录、串口号、ready banner 或 prompt；优先从 `doctor`、当前配置和源码获取。
7. 不要把 build pass 当成完成；功能、调试和测试目标都必须有 UART、diag、monitor 或 remote-dt 证据闭环。
8. `agent_workbench/tests/*.py` 是 Agent Workbench 平台自测，不是迁移项目固件验证入口；除非正在修改平台本身，否则不要把它当作 STM32 项目测试。

## 稳定命令入口

优先从仓库根目录运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

如果 bat 调用失败，使用 direct Python 兜底：

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

如果 `python` 不在 PATH，再试：

```powershell
py -3 ".\agent_workbench\workbench.py" doctor --json
```

所有子命令都按这个模式替换。不要默认使用 `cmd /c ".\agent_workbench.bat ..."`。

## 默认工作模型

1. 先运行 `doctor --json`。如果有阻塞性失败，停止并报告具体失败项。
2. 根据目标修改源码或配置。
3. 运行 `build --json`。失败时运行 `fix-build --json`，结合 build log 小步修复，最多 3 轮。
4. 需要实机闭环时运行 `flash --json` 和/或 `reset --json`。
5. 用 `uart exec`、`diag exec`、`monitor start/stop/stats` 或 `remote-dt` 采集证据。
6. 输出报告时明确列出实际执行的命令、exit_code 和 artifact 路径。未执行的实机验证必须写明“未执行”或“环境/硬件阻塞”。

## 失败优先级

1. 环境或硬件阻塞：读 `doctor_report.json`、flash JSON、UART/diag/monitor/remote-dt evidence，停止并报告阻塞。
2. 命令启动失败：用 direct Python 兜底重试一次，仍失败就报告 launcher 阻塞。
3. 编译失败：运行 `fix-build --json`，结合 build log 小步修复。
4. ready/prompt/CLI 失败：读 `cli_diag.json`、`cli_transcript.log` 分层排查。
5. monitor 失败：检查 `agent_workbench.yaml`、ELF 路径、symbol/address/value_type、OpenOCD/debug 连接。
6. remote-dt 失败：读 `dt_remote_result.json`、`dt_remote_summary.md` 和 `logs/dt_*.log`。
