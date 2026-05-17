# STM32 Agent Workbench 迁移指南

本文说明如何把当前精简版 `agent_workbench` 迁移到另一个 STM32 项目。迁移成功的标准不是“文件复制过去了”，而是目标项目能用当前支持的命令形成最小证据闭环。

当前支持的命令以 `agent_workbench/README.md` 为准。迁移过程中不要使用历史文档里的旧入口，例如 `scan-project`、`integration`、`verify current`、`session`、`context`、`plan`、`monitor probe/run`。

## 1. 迁移验收标准

一次合格迁移至少满足：

1. `doctor --json` 返回 `exit_code = 0`，且 `details.fail_count = 0`。
2. `build --json` 能在目标项目真实构建目录生成目标 ELF，或明确说明该项目暂不支持 CMake 构建。
3. 如果需要烧录，`flash --json` 返回成功，并有真实 flash 日志。
4. 如果项目有 UART CLI，`uart exec --reset-first --expect-ready ... --json` 能看到目标项目真实 ready banner 和 prompt。
5. 如果项目有诊断串口，`diag exec --json` 使用目标项目真实协议帧，而不是示例帧。
6. 如果使用 monitor，`monitor start/stop/stats --json` 能产生目标项目真实变量或地址样本。
7. 如果使用 remote-dt，`remote-dt pipeline --json` 能拉回远端日志和结果摘要。

未达到这些结果时，只能说“文件已复制”或“配置部分完成”，不能说迁移完成。

## 2. 迁移前准备

目标项目建议具备：

- Windows + PowerShell 本地环境。
- 可用 Python，且能安装 `agent_workbench/requirements.txt`。
- CMake 工程，或至少有清晰的构建替代方案。
- 明确的工具链文件、构建目录和 ELF 输出路径。
- 如需实机验证，已连接 ST-Link/OpenOCD 支持的调试器。
- 如需 UART，知道真实串口号、波特率、ready banner、prompt 和可执行 CLI 命令。
- 如需 diag，知道真实串口参数和请求帧。
- 如需 monitor，知道应观察的符号、地址或寄存器，并能说明来源。

不要从源项目复制这些值后直接信任：

- `COM3`
- `STM32 UART CLI ready.`
- `cli>`
- `build/cmake-debug/serial.elf`
- OpenOCD target 脚本
- `monitor.items`
- 任何外设寄存器地址或 RAM 地址

这些都必须在目标项目中重新确认。

## 3. 复制哪些文件

推荐复制：

```text
agent_workbench/
```

如果目标项目根目录没有外层启动脚本，也可以只使用内层入口：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

可选复制或新建外层便捷脚本，但不是当前 workbench 的必要条件。

不建议把以下运行产物作为迁移真源：

```text
agent_workbench/runtime/
agent_workbench/generated/
agent_workbench/evidence/
agent_workbench/__pycache__/
agent_workbench/core/__pycache__/
```

这些目录可以保留作历史参考，但目标项目的验收必须使用目标项目重新生成的产物。

## 4. 配置目标项目

迁移核心是修改：

```text
agent_workbench/agent_workbench.yaml
```

### 4.1 项目路径

优先确认：

```yaml
project:
  name: your_project
  root: ..
  cmake_source_dir: .
  build_dir: build/cmake-debug
  artifact_file: build/cmake-debug/your_project.elf
  artifact_elf: build/cmake-debug/your_project.elf
  compile_commands: build/cmake-debug/compile_commands.json
  source_dirs:
    - Core
    - Drivers
    - cmake
    - agent_workbench
```

规则：

- `root` 是相对 `agent_workbench/` 的项目根路径；workbench 放在项目根下时通常是 `..`。
- `cmake_source_dir` 是包含 `CMakeLists.txt` 的目录，相对 `project.root`。
- `build_dir`、`artifact_file`、`compile_commands` 必须指向同一套构建输出。
- `source_dirs` 用于让 agent 理解源码范围，不要遗漏真实业务源码目录。

### 4.2 CMake 与工具链

确认：

```yaml
tools:
  cmake:
    generator: MinGW Makefiles
    build_type: Debug
    toolchain_file: cmake/arm-none-eabi-toolchain.cmake
    configure_args: []
    build_args:
      - -j
```

常见问题：

- 目标项目使用 Ninja，却仍写 `MinGW Makefiles`。
- toolchain 文件路径沿用了源项目。
- `cmake_source_dir` 不对，导致 CMake 找不到 `CMakeLists.txt`。

### 4.3 OpenOCD、flash 和 reset

确认：

```yaml
tools:
  openocd:
    config_files:
      - interface/stlink.cfg
      - target/stm32f1x.cfg
    daemon_cmd: openocd -l "{openocd_live_log_posix}" -f interface/stlink.cfg -f target/stm32f1x.cfg -c "gdb port 3333; tcl port 6666; telnet_port 4444"
  flash:
    default_method: openocd_cmd
    methods:
      openocd_cmd:
        flash: openocd -f interface/stlink.cfg -f target/stm32f1x.cfg -c "program {artifact_elf_posix} verify reset exit"
        reset: openocd -f interface/stlink.cfg -f target/stm32f1x.cfg -c "init; reset run; shutdown"
```

迁移到不同 MCU 系列时，必须更换 target 脚本。例如 F1 项目的 `target/stm32f1x.cfg` 不应直接用于 F4/H7/L4 项目。

### 4.4 UART CLI

如果目标项目有 CLI：

```yaml
uart:
  enabled: true
  port: COM7
  baudrate: 115200
  ready_banner: Target CLI ready.
  prompt: cli>
  probe_commands:
    - help
    - status
```

如果没有 CLI：

```yaml
uart:
  enabled: false
```

注意：

- `ready_banner` 和 `prompt` 必须与固件实际输出完全匹配。
- `probe_commands` 必须是目标固件真正支持的命令。
- `uart exec --expect-ready` 依赖 ready banner；如果目标固件不打印 ready，应关闭 expect-ready 或调整固件/配置。

### 4.5 诊断串口

如果目标项目有原始诊断协议：

```yaml
diag_uart:
  enabled: true
  port: COM8
  baudrate: 115200
  default_hex_requests:
    - 01 03 00 00 00 02 C4 0B
```

如果没有：

```yaml
diag_uart:
  enabled: false
```

不要沿用示例中的 `help\r\n`、`status\r\n` 十六进制帧，除非目标项目诊断口确实就是文本 CLI。

### 4.6 Monitor

如果暂时不用 monitor，可先关闭：

```yaml
monitor:
  enabled: false
```

如果需要采样：

```yaml
monitor:
  enabled: true
  sample_hz: 100
  symbols:
    elf_path: build/cmake-debug/your_project.elf
  items:
    - name: app_state
      source: symbol
      symbol: g_app_state
      value_type: u32
```

要求：

- `symbols.elf_path` 与当前烧录 ELF 一致。
- `source: symbol` 的符号必须能在 ELF 中找到。
- `source: memory` 的地址必须来自 map、链接脚本、CMSIS 头文件、设备手册或 runtime evidence。
- `value_type` 与真实数据宽度一致。

### 4.7 Remote DT

如果不用远程 DT：

```yaml
remote_dt:
  enabled: false
```

如果启用：

```yaml
remote_dt:
  enabled: true
  host: "192.168.1.50"
  user: "dtuser"
  port: 22
  remote_project_dir: "/home/dtuser/projects/your_project"
  local_artifact_dir: agent_workbench/runtime/remote_dt
  scripts:
    build: ./build.sh
    execute: ./execute.sh
    coverage: ./gen_coverage.sh
```

远端项目目录必须已经存在，并且脚本能在远端手动执行。

## 5. 安装依赖

在目标项目根目录运行：

```powershell
.\agent_workbench\bin\setup.bat
```

如果只想手动检查依赖，至少确保：

- `PyYAML` 可用。
- 如需串口能力，建议安装 `pyserial`。
- `cmake` 可在 PATH 中找到。
- 如需烧录/monitor，`openocd` 可在 PATH 中找到。
- 如需 remote-dt，`ssh` 和 `scp` 可在 PATH 中找到。

`doctor` 在 pyserial 缺失时可能仍可使用 PowerShell fallback 执行部分 UART/diag 操作，但长期建议安装 pyserial。

## 6. 基础验收顺序

### 6.1 doctor

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

看：

- `exit_code`
- `details.fail_count`
- `details.warn_count`
- `details.results[]`
- `artifacts.report_json`
- `artifacts.report_md`

常见 warn：

- `artifact_file`：还没构建或 ELF 路径不对。
- `compile_commands`：还没构建或路径不对。
- `uart_port`：串口未连接或被占用。
- `diag_uart_port`：诊断口未连接或被占用。

常见 fail：

- Python/YAML 不可用。
- 输出目录不可写。
- CMake 不存在。
- toolchain 文件不存在。
- `hardware.mode = required` 时硬件工具或端口不可用。

### 6.2 build

```powershell
.\agent_workbench\bin\agent_workbench.bat build --json
```

失败时：

```powershell
.\agent_workbench\bin\agent_workbench.bat fix-build --json
```

优先读 `runtime/build.log`，不要只看终端摘要。

### 6.3 flash 和 reset

```powershell
.\agent_workbench\bin\agent_workbench.bat flash --json
.\agent_workbench\bin\agent_workbench.bat reset --json
```

如果失败，检查：

- `project.artifact_file`
- `tools.flash.default_method`
- OpenOCD interface 和 target 脚本
- 板卡供电、连接、占用情况

### 6.4 UART CLI

```powershell
.\agent_workbench\bin\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json
```

如果目标项目没有 `help/status`，替换成真实命令。

失败时读：

- `runtime/cli_transcript.log`
- `runtime/cli_diag.json`
- `runtime/uart_exec_reset.log`

### 6.5 Diag

```powershell
.\agent_workbench\bin\agent_workbench.bat diag exec --json
```

或：

```powershell
.\agent_workbench\bin\agent_workbench.bat diag exec --hex "01 03 00 00 00 02 C4 0B" --json
```

失败时读：

- `runtime/diag_exchange.log`
- `runtime/diag_exec_result.json`

### 6.6 Monitor

```powershell
.\agent_workbench\bin\agent_workbench.bat monitor start --reset-first --json
.\agent_workbench\bin\agent_workbench.bat monitor stop --json
.\agent_workbench\bin\agent_workbench.bat monitor stats --json
```

必要时在 start 和 stop 之间执行 UART/diag 动作，让 monitor 捕获状态变化。

重点产物：

- `runtime/monitor_live/monitor_samples.csv`
- `runtime/monitor_live/monitor_samples_wide.csv`
- `runtime/monitor_live/monitor_samples.jsonl`
- `runtime/monitor_live/monitor_session.jsonl`

### 6.7 Remote DT

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt build --json
.\agent_workbench\bin\agent_workbench.bat remote-dt pipeline --json
```

第一次迁移建议先跑单独 build，再跑完整 pipeline。

## 7. 迁移故障速查

| 现象 | 优先检查 |
|---|---|
| `toolchain_file` fail | `tools.cmake.toolchain_file` 是否指向目标项目真实文件 |
| `artifact_file` 一直 warn | 是否已经 build；`artifact_file` 是否与实际 ELF 名称一致 |
| `compile_commands` warn | CMake 是否生成 `compile_commands.json`；路径是否一致 |
| build 找不到源码或 CMakeLists | `project.root`、`project.cmake_source_dir` |
| flash 连接不上 | OpenOCD target、interface、板卡供电、ST-Link 占用 |
| UART 找不到 ready | 端口、波特率、ready 字符串、固件是否复位后打印 ready |
| UART 找不到 prompt | prompt 配置是否与固件一致；命令是否卡住未返回 |
| diag 超时 | 请求帧是否真实；端口和波特率是否正确；协议是否需要 CRC/长度 |
| monitor 无样本 | OpenOCD 是否启动；`monitor.enabled`；items 是否为空 |
| monitor 符号找不到 | `monitor.symbols.elf_path` 与 ELF 是否一致；符号是否被优化或声明为 static |
| remote-dt 配置失败 | `enabled`、`host`、`user`、`remote_project_dir` |
| remote-dt pull 失败 | 远端日志目录、结果目录、覆盖率目录是否真实存在 |

## 8. 最小迁移清单

按顺序执行：

1. 复制 `agent_workbench/` 到目标项目根目录。
2. 修改 `agent_workbench/agent_workbench.yaml` 的 `project`、`tools`、`uart`、`diag_uart`、`monitor`、`remote_dt`。
3. 运行 `.\agent_workbench\bin\setup.bat`。
4. 运行 `doctor --json`，修到 `fail_count = 0`。
5. 运行 `build --json`，失败时用 `fix-build --json` 辅助定位。
6. 需要硬件时运行 `flash --json` 和 `reset --json`。
7. 有 CLI 时运行 `uart exec --reset-first --expect-ready ... --json`。
8. 有诊断协议时运行 `diag exec --json`。
9. 有内部状态观察需求时运行 `monitor start/stop/stats --json`。
10. 有远程 Linux 流水线时运行 `remote-dt build --json`，再运行 `remote-dt pipeline --json`。

做到这一步，才可以把目标项目交给 agent 做后续功能开发、调试或测试设计。
