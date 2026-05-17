# STM32 Agent Workbench 设计与维护指南

本文面向维护者、迁移者和使用 Agent Workbench 驱动 STM32 项目的 agent。它描述的是当前精简后的 workbench，不再记录已删除的历史命令。

当前版本的设计目标很明确：保留一组小而稳定的命令，把 STM32 项目的环境检查、构建、烧录、复位、UART CLI 验证、诊断串口、运行态监控和远程 DT 流水线都收束到可审计的 JSON 与 artifact 中。

## 1. 当前能力边界

`agent_workbench` 不是固件框架，也不是 IDE 插件。它是一个位于仓库内的自动化控制面，负责把常见工程动作标准化：

- 环境和配置检查：`doctor --json`
- CMake 构建和构建错误结构化：`build --json`、`fix-build --json`
- 实机动作：`flash --json`、`reset --json`
- UART CLI 黑盒验证：`uart exec ... --json`
- 原始诊断串口收发：`diag exec --json`
- OpenOCD 运行态采样：`monitor start/stop/stats --json`
- 远程 Linux DT 构建、执行、覆盖率和日志拉取：`remote-dt ... --json`

任何文档、skill 或 agent 提示词只要引用了下面这些旧入口，就已经过期，应删除或改写：

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
- `init-opencode-agents`

## 2. 稳定命令入口

所有命令默认从仓库根目录运行。优先使用内层 bat 入口：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

如果 bat 入口启动失败，再使用 direct Python 兜底：

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

如果 `python` 不在 PATH，再试：

```powershell
py -3 ".\agent_workbench\workbench.py" doctor --json
```

PowerShell 中一次只运行一条 workbench 命令。不要把多个 workbench 命令用 `;`、`&&` 或管道串在一起。每个支持 JSON 的公开命令都应加 `--json`，报告必须引用真实 JSON、日志或 artifact。

## 3. 公开命令矩阵

| 命令 | 主要作用 | 关键产物 |
|---|---|---|
| `doctor --json` | 检查 Python、YAML、输出目录、CMake、toolchain、ELF、OpenOCD、flash 方法、UART、diag、monitor 配置 | `agent_workbench/runtime/doctor_report.json`、`doctor_report.md` |
| `build --json` | 执行 `cmake -S/-B` 和 `cmake --build`，解析 GCC/linker 错误 | `agent_workbench/runtime/build.log` |
| `fix-build --json` | 从最近构建日志提取结构化修复建议 | JSON 输出中的 `suggested_fixes` |
| `flash --json` | 按配置烧录当前 ELF | `agent_workbench/runtime/flash.log` |
| `reset --json` | 按配置复位目标板 | `agent_workbench/runtime/reset.log` |
| `uart exec --reset-first --json` | 复位后执行 CLI 命令批次 | `cli_transcript.log`、`cli_diag.json`、`uart_exec_reset.log` |
| `uart exec --reset-first --expect-ready --json` | 复位后等待 ready banner，再执行 CLI 命令批次 | 同上 |
| `diag exec --json` | 发送诊断串口十六进制请求并记录响应 | `diag_exchange.log`、`diag_exec_result.json` |
| `monitor start --json` | 启动 OpenOCD 和后台监控采样进程 | `runtime/monitor_live/*`、`runtime/pids/monitor.pid` |
| `monitor start --reset-first --json` | 启动监控并让目标板 reset run | 同上 |
| `monitor stop --json` | 请求停止监控，必要时清理后台进程和 OpenOCD | `monitor.stop`、`monitor_session.jsonl` |
| `monitor stats --json` | 汇总监控 CSV 的采样频率和样本数 | 默认读取 `monitor_live/monitor_samples.csv` |
| `remote-dt build --json` | 在远程 Linux 运行 build 脚本并拉回日志 | `runtime/remote_dt/*` |
| `remote-dt execute --json` | 在远程 Linux 运行 execute 脚本并拉回日志 | 同上 |
| `remote-dt coverage --json` | 在远程 Linux 运行 coverage 脚本并拉回覆盖率目录 | 同上 |
| `remote-dt pipeline --json` | 顺序执行 build、execute、coverage，失败后跳过后续阶段 | `dt_remote_result.json`、`dt_remote_summary.md` |
| `remote-dt pull-logs --json` | 只拉回远端已有日志、结果和覆盖率目录 | 同上 |

`uart exec` 实际使用时通常还需要 `--command` 或 `--script`。例如：

```powershell
.\agent_workbench\bin\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json
```

`diag exec` 可以不传参数，此时使用 `agent_workbench.yaml` 中的 `diag_uart.default_hex_requests`；也可以传 `--hex` 或 `--script`：

```powershell
.\agent_workbench\bin\agent_workbench.bat diag exec --hex "68 65 6C 70 0D 0A" --json
```

## 4. 架构分层

仓库中的职责边界如下：

| 位置 | 职责 |
|---|---|
| `agent_workbench/README.md` | 当前支持命令的最短权威入口 |
| `agent_workbench/workbench.py` | CLI 解析、命令分发、JSON payload 封装 |
| `agent_workbench/agent_workbench.yaml` | 单一配置源，定义项目路径、构建、烧录、UART、diag、monitor、remote-dt |
| `agent_workbench/bin/agent_workbench.bat` | Windows 稳定启动器 |
| `agent_workbench/bin/setup.bat` | Python 依赖安装和基础检查入口 |
| `agent_workbench/core/config.py` | 配置默认值合并、路径解析、模板变量生成 |
| `agent_workbench/core/doctor.py` | 环境与配置检查 |
| `agent_workbench/core/build_service.py` | CMake 配置与构建 |
| `agent_workbench/core/build_errors.py` | 构建日志解析与修复建议 |
| `agent_workbench/core/flash_service.py` | 烧录与复位命令执行 |
| `agent_workbench/core/uart_service.py` | UART CLI 批处理、ready/prompt 检测、transcript 记录 |
| `agent_workbench/core/cli_diag_service.py` | CLI 失败分类和 `cli_diag.json` 生成 |
| `agent_workbench/core/diag_uart_service.py` | 原始十六进制诊断串口收发 |
| `agent_workbench/core/monitor_service.py` | OpenOCD 后台采样、CSV/JSONL 导出、统计汇总 |
| `agent_workbench/core/openocd_service.py` | OpenOCD 后台进程管理 |
| `agent_workbench/core/openocd_client.py` | OpenOCD telnet 读寄存器/读内存/控制目标 |
| `agent_workbench/core/remote_dt_service.py` | SSH/SCP 远程 DT 阶段执行、日志拉取、结果摘要 |
| `agent_workbench/core/symbols.py` | ELF 符号解析 |
| `agent_workbench/core/serial_settings.py` | pyserial 与 PowerShell 串口参数统一 |

`runtime/`、`generated/`、`evidence/` 是产物目录，不应被当作源代码真源维护。当前精简版核心证据主要写在 `runtime/`。

## 5. 配置模型

`agent_workbench.yaml` 是当前 workbench 的单一事实来源。不要在文档、提示词或脚本里硬编码串口号、ready banner、prompt、ELF 路径、OpenOCD target、monitor 地址或远程服务器信息。

维护时重点关注这些配置段：

| 段落 | 关键字段 |
|---|---|
| `project` | `name`、`root`、`cmake_source_dir`、`build_dir`、`artifact_file`、`compile_commands`、`source_dirs` |
| `outputs` | `runtime_root`、`evidence_root`、`generated_root` |
| `hardware` | `mode`，决定硬件不可用时是失败还是警告 |
| `tools.cmake` | `generator`、`build_type`、`toolchain_file`、`configure_args`、`build_args` |
| `tools.openocd` | `config_files`、`extra_commands`、`daemon_cmd`、`host`、`telnet_port` |
| `tools.flash` | `default_method`、`methods.*.flash`、`methods.*.reset` |
| `uart` | `enabled`、`port`、`baudrate`、`ready_banner`、`prompt`、`probe_commands`、timeout |
| `diag_uart` | `enabled`、`port`、`baudrate`、`default_hex_requests`、timeout |
| `monitor` | `enabled`、`sample_hz`、`symbols.elf_path`、`items`、OpenOCD 连接参数 |
| `remote_dt` | `enabled`、`host`、`user`、`remote_project_dir`、`scripts`、`timeouts`、`artifacts` |

配置修改后第一步永远是：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

如果 `doctor` 有 fail，应先修配置或环境，不要继续写业务代码。

## 6. JSON 与产物约定

公开命令的 JSON 输出通常包含：

- `command`：命令名
- `exit_code`：进程级退出码
- `status`：`pass`、`fail` 或 `blocked`
- `summary`：短摘要
- `details`：命令特有结构化信息
- `artifacts`：本次命令写出的文件路径
- `timestamp`：执行时间

不要猜字段。不同命令的 `details` 结构不同，agent 必须读取实际 JSON。

常用产物：

| 文件 | 说明 |
|---|---|
| `runtime/doctor_report.json` | `doctor` 的机器可读检查结果 |
| `runtime/doctor_report.md` | `doctor` 的人工可读表格 |
| `runtime/build.log` | 完整 CMake/GCC/linker 构建日志 |
| `runtime/flash.log` | 烧录日志 |
| `runtime/reset.log` | 复位日志 |
| `runtime/uart_exec_reset.log` | `uart exec --reset-first` 内部复位日志 |
| `runtime/cli_transcript.log` | UART 收发转录 |
| `runtime/cli_diag.json` | CLI 失败分类 |
| `runtime/diag_exchange.log` | 诊断串口收发日志 |
| `runtime/diag_exec_result.json` | 诊断串口结构化结果 |
| `runtime/monitor_live/monitor_samples.csv` | monitor 长表采样 |
| `runtime/monitor_live/monitor_samples_wide.csv` | monitor 宽表采样 |
| `runtime/monitor_live/monitor_samples.jsonl` | monitor JSONL 采样 |
| `runtime/monitor_live/monitor_snapshot.csv` | 停止时的环形缓冲快照 |
| `runtime/monitor_live/monitor_session.jsonl` | monitor 启停、符号解析和采样元数据 |
| `runtime/remote_dt/dt_remote_result.json` | remote-dt 完整结构化结果 |
| `runtime/remote_dt/dt_remote_summary.md` | remote-dt 人工可读摘要 |

## 7. 标准工作流

### 7.1 修改代码前

先运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

判断方式：

- `exit_code = 0` 且 `details.fail_count = 0`：可以继续。
- 有 fail：停止，报告具体失败项和 artifact。
- 只有 warn：结合任务判断是否阻塞。例如 UART 端口被占用会阻塞 UART 验证，但不一定阻塞纯文档或纯构建任务。

### 7.2 构建闭环

代码修改后运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat build --json
```

失败时运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat fix-build --json
```

`fix-build` 只提供结构化建议，不会自动改源码。维护者应读取 `build.log` 和 `suggested_fixes`，小步修复后重新构建。

### 7.3 实机闭环

构建通过不等于任务完成。需要硬件证据时，按任务选择：

```powershell
.\agent_workbench\bin\agent_workbench.bat flash --json
.\agent_workbench\bin\agent_workbench.bat reset --json
.\agent_workbench\bin\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json
```

如果项目使用诊断串口：

```powershell
.\agent_workbench\bin\agent_workbench.bat diag exec --json
```

如果需要内部状态趋势：

```powershell
.\agent_workbench\bin\agent_workbench.bat monitor start --reset-first --json
.\agent_workbench\bin\agent_workbench.bat monitor stop --json
.\agent_workbench\bin\agent_workbench.bat monitor stats --json
```

`monitor start` 是后台采样。启动后应执行待观察动作，再调用 `monitor stop`，最后用 `monitor stats` 和 CSV/JSONL 样本分析趋势。

## 8. Monitor 设计要点

monitor 的核心约束是：不要臆测符号、地址和寄存器。所有 item 都必须来自当前源码、ELF/map、CMSIS 头文件、设备参考手册或用户明确输入。

常见 item：

```yaml
monitor:
  enabled: true
  symbols:
    elf_path: build/cmake-debug/serial.elf
  items:
    - name: g_data
      source: symbol
      symbol: g_data
      value_type: u32
    - name: adc_latest
      source: memory
      target: 0x200001b0
      value_type: u16
    - name: pc
      source: register
      target: pc
      value_type: u32
```

建议：

- RAM 变量优先使用 `source: symbol`。
- 固定地址必须有来源，不能复制示例地址。
- CPU register 采样会打扰运行态，高频变量采样时通常保持 `register_sample_hz: 0`。
- `monitor.symbols.elf_path` 应与当前烧录的 ELF 一致。
- 采样前先让 `doctor` 确认 `monitor_symbol_image`、`monitor_items` 和 OpenOCD 状态。

## 9. Remote DT 设计要点

`remote-dt` 用于把本地 Windows 项目的验证动作下发到远程 Linux。它不负责同步源码；它假设远程 `remote_project_dir` 已经是待验证项目。

本地动作：

- 通过 SSH 登录远程服务器。
- 在远端项目目录执行配置的脚本。
- 将远端日志、结果 JSON 和覆盖率目录拉回本地。
- 在本地生成统一的 `dt_remote_result.json` 与 `dt_remote_summary.md`。

流水线顺序：

1. `build`
2. `execute`
3. `coverage`

前一阶段失败时，后续阶段会标记为 skipped。失败分析优先看 `dt_remote_summary.md`，再看对应 `logs/dt_*.log`。

## 10. 失败分层

遇到失败时按下面顺序定位：

1. `doctor` fail：环境或配置阻塞，先修 `agent_workbench.yaml`、工具链、路径、权限或串口占用。
2. launcher 失败：bat 入口失败时用 direct Python 兜底。
3. `build` 失败：读 `build.log` 和 `fix-build` JSON，先处理第一处真实编译/链接错误。
4. `flash/reset` 失败：读对应日志，检查 OpenOCD target、ST-Link、ELF 路径和板卡供电。
5. `uart exec` 失败：同时读 `cli_transcript.log` 与 `cli_diag.json`，区分 ready 缺失、prompt 缺失、命令超时和串口占用。
6. `diag exec` 失败：检查端口、十六进制请求帧、波特率、协议回复时序。
7. `monitor` 失败：检查 OpenOCD 连接、ELF 符号、item 地址、value_type、目标板运行状态。
8. `remote-dt` 失败：读 `dt_remote_result.json`、`dt_remote_summary.md` 和 `logs/dt_*.log`。

## 11. 维护原则

- README 是当前命令列表的最短权威来源；docs 只能扩展解释，不能发明新入口。
- 每增加或删除一个公开命令，必须同步更新 README、本文和相关 skill reference。
- 不要把 `agent_workbench/tests/*.py` 当作固件验证入口；它们是 workbench 平台自测。
- 文档中的命令必须可以在当前 `workbench.py` 中找到。
- 硬件参数、寄存器地址、内存地址、定时器参数、串口协议都必须来自当前项目证据。
- 最终报告应列出真实执行命令、exit_code 和 artifact 路径；未执行的硬件验证要明确说明未执行原因。

一句话总结：

> 当前 Agent Workbench 的价值不在于命令多，而在于用少量稳定命令把 STM32 开发验证变成可重复、可审计、可迁移的证据链。
