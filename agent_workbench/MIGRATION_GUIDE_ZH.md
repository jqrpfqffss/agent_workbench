# agent_workbench 迁移与适配指南

## 1. 这份文档是干什么的

这份文档专门用来指导你把当前仓库里的 `agent_workbench` 迁移到另一个 STM32 项目中，并完成最基本的适配，让它真正能用来做：

- 自动化调试
- 自动化测试
- 自动化功能验证
- VS Code + Continue Agent 协同工作

这份文档按“小白也能照着做”的方式来写。

## 2. 先说结论：最推荐的迁移方式

最稳妥的方法不是“只抠几个脚本文件”，而是：

1. 把整个 `agent_workbench/` 目录复制到新项目根目录
2. 把项目根目录下这两个入口脚本也复制过去：
   - `agent_workbench.bat`
   - `setup_workbench.bat`
3. 修改 `agent_workbench/agent_workbench.yaml`
4. 根据新项目实际命令改 `agent_workbench/tasks/*.yaml`
5. 执行：
   - `setup_workbench.bat`
   - `agent_workbench.bat doctor`
   - `agent_workbench.bat init-vscode`
   - `agent_workbench.bat build`

如果你图省事，直接整目录复制是对的。之后再把不需要的历史运行痕迹删掉即可。

## 3. 迁移前先确认新项目是否满足这些前提

当前这套 `agent_workbench` 有几个现实前提：

### 3.1 构建默认基于 CMake

当前 `agent_workbench/core/build_service.py` 只会调用：

- `cmake -S . -B ...`
- `cmake --build ...`

所以：

- 如果你的新项目已经是 CMake 项目，直接适配配置即可
- 如果你的新项目还不是 CMake 项目，建议先把它改成 CMake，再迁移 workbench

如果你不先补 CMake，这套 workbench 现在不能直接替你构建。

### 3.2 当前文档和脚本默认针对 Windows

当前仓库里的入口是：

- `agent_workbench.bat`
- `setup_workbench.bat`

所以本文默认你是在 Windows 环境里迁移和使用。

### 3.3 如果你要用 UART CLI 自动验证

新项目最好满足这些条件：

- 固件有稳定的 UART CLI
- 有明确的 ready banner
- 有稳定的 prompt
- 串口参数固定

例如：

- ready banner：`STM32 UART CLI ready.`
- prompt：`cli>`

如果没有这些，workbench 也能迁移，但 UART 自动探测能力会弱很多。

## 4. 需要复制哪些文件

## 4.1 必须复制

把下面这些带到新项目根目录：

### 项目根目录下

- `agent_workbench.bat`
- `setup_workbench.bat`

### `agent_workbench/` 目录下

- `agent_workbench.yaml`
- `workbench.py`
- `requirements.txt`
- `bin/`
- `core/`
- `checks/`
- `prompts/`
- `tasks/`
- `tests/`
- `README.md`
- `VS_CODE_CONTINUE_GUIDE.md`
- `VS_CODE_CONTINUE_GUIDE_ZH.md`
- `MIGRATION_GUIDE_ZH.md`

## 4.2 建议复制

如果你希望保留参考示例，也建议复制：

- `agent_workbench/examples/`
- `agent_workbench/templates/`

## 4.3 不建议带过去的历史文件

下面这些不是“源代码”，是运行过程中自动生成的内容。迁移到新项目时，通常不要带历史垃圾：

- `agent_workbench/runtime/`
- `agent_workbench/evidence/`
- `agent_workbench/generated/`
- `agent_workbench/__pycache__/`
- `agent_workbench/core/__pycache__/`
- `agent_workbench/tests/__pycache__/`

如果你是直接整目录复制过去，也没关系。复制后把这些目录删掉即可。

## 4.4 `.vscode/tasks.json` 要不要复制

不建议直接复制旧项目里的 `.vscode/tasks.json`。

正确做法是：

1. 先迁移 `agent_workbench`
2. 再执行：

```powershell
agent_workbench.bat init-vscode
```

这样 workbench 会为新项目重新生成 `.vscode/tasks.json`。

## 5. 新项目里的推荐目录结构

建议新项目最终长这样：

```text
your_project/
├─ agent_workbench/
├─ agent_workbench.bat
├─ setup_workbench.bat
├─ CMakeLists.txt
├─ Core/
├─ Drivers/
└─ ...
```

## 6. 迁移后第一步：改 `agent_workbench.yaml`

这是最重要的一步。

你后面几乎所有动作，都会依赖：

- `agent_workbench/agent_workbench.yaml`

## 6.1 必改项总览

你至少要检查这些字段：

### `project`

- `project.name`
- `project.root`
- `project.build_dir`
- `project.artifact_elf`
- `project.compile_commands`
- `project.source_dirs`

### `tools.cmake`

- `tools.cmake.generator`
- `tools.cmake.build_type`
- `tools.cmake.toolchain_file`
- `tools.cmake.configure_args`
- `tools.cmake.build_args`

### `tools.openocd`

- `tools.openocd.daemon_cmd`
- `tools.openocd.host`
- `tools.openocd.telnet_port`

### `tools.flash`

- `tools.flash.default_method`
- `tools.flash.methods.stlink_cli.flash`
- `tools.flash.methods.stlink_cli.reset`
- `tools.flash.methods.openocd_cmd.flash`
- `tools.flash.methods.openocd_cmd.reset`

### `uart`

- `uart.enabled`
- `uart.port`
- `uart.baudrate`
- `uart.ready_banner`
- `uart.prompt`
- `uart.probe_commands`
- `uart.help_rows`

### `monitor`

- `monitor.enabled`
- `monitor.symbols.elf_path`
- `monitor.items`

### `checks`

- `checks.unit.enabled`
- `checks.unit.command`

### `workflow`

- `workflow.manage_openocd`
- `workflow.observe_seconds`
- `workflow.auto_compare_previous`
- `workflow.verify_sequence`

## 6.2 一项一项怎么改

### 6.2.1 `project.name`

改成你的项目名。

例如：

```yaml
project:
  name: my_stm32_cli
```

### 6.2.2 `project.root`

这是“项目根目录相对于 `agent_workbench/` 的位置”。

如果 `agent_workbench/` 就放在项目根目录下，一般写：

```yaml
project:
  root: ..
```

通常不用改。

### 6.2.3 `project.build_dir`

改成你的 CMake 构建输出目录。

例如：

```yaml
project:
  build_dir: build/cmake-debug
```

### 6.2.4 `project.artifact_elf`

改成构建出来的 `.elf` 文件路径。

例如：

```yaml
project:
  artifact_elf: build/cmake-debug/my_stm32_cli.elf
```

### 6.2.5 `project.compile_commands`

改成 `compile_commands.json` 的路径。

例如：

```yaml
project:
  compile_commands: build/cmake-debug/compile_commands.json
```

### 6.2.6 `project.source_dirs`

改成你项目实际的源码目录列表。

例如：

```yaml
project:
  source_dirs:
    - Core
    - Drivers
    - Middlewares
    - App
    - cmake
```

### 6.2.7 `tools.cmake.toolchain_file`

改成你的 Arm GCC toolchain 文件路径。

例如：

```yaml
tools:
  cmake:
    toolchain_file: cmake/arm-none-eabi-toolchain.cmake
```

如果这里写错，`doctor` 和 `build` 都会很难看。

### 6.2.8 `tools.openocd.daemon_cmd`

如果你还是 ST-Link + OpenOCD + STM32F1/F4/F7 这类常见组合，通常只需要改 target cfg。

例如：

```yaml
tools:
  openocd:
    daemon_cmd: openocd -l "{openocd_live_log_posix}" -f interface/stlink.cfg -f target/stm32f4x.cfg -c "gdb_port 3333; tcl_port 6666; telnet_port 4444"
```

如果芯片型号变了，`target/*.cfg` 往往要跟着变。

### 6.2.9 `tools.flash.methods.*`

这里决定 `flash` 和 `reset` 怎么做。

如果你用 OpenOCD，就改 `openocd_cmd`。

如果你用 STM32_Programmer_CLI，就改 `stlink_cli`。

你只要保证两件事：

1. `flash` 命令真的能烧录
2. `reset` 命令真的能复位

### 6.2.10 `uart.port`

改成新项目板子接到的串口号。

例如：

```yaml
uart:
  port: COM7
```

这是最常见的出错点之一。

### 6.2.11 `uart.baudrate`

改成固件真实波特率。

例如：

```yaml
uart:
  baudrate: 115200
```

### 6.2.12 `uart.ready_banner`

改成固件启动后输出的欢迎语。

例如固件输出：

```text
MyBoard CLI ready.
```

那就写：

```yaml
uart:
  ready_banner: MyBoard CLI ready.
```

如果这里写错，`uart exec --expect-ready` 会一直报握手失败。

### 6.2.13 `uart.prompt`

改成 CLI 提示符。

例如：

```yaml
uart:
  prompt: cli>
```

或者：

```yaml
uart:
  prompt: shell#
```

### 6.2.14 `uart.probe_commands`

改成你的项目最适合做 smoke 的命令。

推荐选择：

- 不危险
- 可重复执行
- 有明确文本输出
- 容易自动断言

例如：

```yaml
uart:
  probe_commands:
    - help
    - status
    - version
```

### 6.2.15 `uart.help_rows`

这是给 `uart console` 和文档展示用的命令说明，不影响核心执行，但建议同步改。

例如：

```yaml
uart:
  help_rows:
    - command: help
      detail: "list commands | usage: help | args: none"
    - command: version
      detail: "show firmware version | usage: version | args: none"
```

### 6.2.16 `monitor.enabled`

如果你暂时不打算用 OpenOCD 监控变量，先关掉：

```yaml
monitor:
  enabled: false
```

这样迁移初期会更省心。

### 6.2.17 `checks.unit.command`

如果你保留当前默认的 Python unittest，就可以先不改。

如果你项目要跑别的测试命令，比如：

- `ctest`
- `pytest`
- 自定义脚本

就把它改掉。

例如：

```yaml
checks:
  unit:
    enabled: true
    command: ctest --test-dir "{build_dir}" --output-on-failure
```

## 7. 新项目里的任务文件也要改

除了 `agent_workbench.yaml`，还要改：

- `agent_workbench/tasks/*.yaml`

因为 task 文件定义了：

- 目标
- 作用范围
- 验收条件
- 要跑哪些 CLI 命令

## 7.1 最少要改哪些字段

每个 task 至少检查这些：

- `id`
- `mode`
- `goal`
- `scope.include`
- `scope.exclude`
- `acceptance.blackbox`
- `acceptance.unit`
- `observability.notes`
- `verify.sequence`
- `verify.cli_commands`

## 7.2 怎么改 blackbox 断言

blackbox 断言必须改成你新项目真实会输出的内容。

例如旧项目里有：

```yaml
- name: cli_status_reports_uart
  type: cli_contains
  needle: "UART: USART2 @ 115200 8N1"
```

如果你的新项目 status 输出是：

```text
UART1 115200 8N1
```

那就必须改成：

```yaml
- name: cli_status_reports_uart
  type: cli_contains
  needle: "UART1 115200 8N1"
```

不改的话，功能明明正常，也会被 workbench 判失败。

## 7.3 建议先准备两份 task

建议你迁移后至少先准备两份 task：

### 1. 硬件 smoke task

只验证最小链路：

- 上电欢迎语
- prompt
- `help`
- `status`

### 2. 功能回归 task

验证核心命令闭环：

- 关键控制命令
- 关键状态命令
- 关键 ACK 输出

## 8. 要不要改 prompts

通常不用大改，但建议至少保留这些：

- `prompts/continue_debug.md`
- `prompts/continue_feature.md`
- `prompts/continue_test_author.md`
- `prompts/continue_report.md`
- `prompts/continue_agent_zh.md`

如果你想让 Continue 的提示更贴近新项目，可以改：

- 项目名
- 命令名
- 常见证据文件
- 常见排查重点

## 9. `DebugCliStats` 要不要做

如果你的新项目也想享受更强的 CLI 失败分类能力，建议固件里暴露一个全局符号：

- `DebugCliStats`

当前 workbench 读取它后，失败时能更好地区分：

- `rx_zero`
- `parser_no_command`
- `tx_or_host_rx`

如果你不做这个符号，也能跑，但失败时诊断信息会弱一些，可能变成：

- `diag_unavailable`

## 10. 迁移后的第一次启动步骤

假设你已经把文件复制好了，也改完了配置，第一次建议严格按下面顺序跑。

### 第 1 步：安装依赖

```powershell
setup_workbench.bat
```

如果你电脑上有多个 Python，建议先设置：

```powershell
set AGENT_WORKBENCH_PYTHON=C:\Path\To\python.exe
```

说明：

- 现在脚本已经支持新的 `AGENT_WORKBENCH_PYTHON`
- 旧的 `SMARTFARM_PYTHON` 也仍然兼容

### 第 2 步：环境体检

```powershell
agent_workbench.bat doctor
```

看 `doctor_report.md` 是否有这些关键项：

- `toolchain_file`
- `artifact_elf`
- `compile_commands`
- `openocd`
- `flash_method`
- `uart_protocol`
- `uart_backend`

### 第 3 步：生成 VS Code 任务

```powershell
agent_workbench.bat init-vscode
```

### 第 4 步：先试构建

```powershell
agent_workbench.bat build
```

### 第 5 步：先试最小 smoke

```powershell
agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status
```

### 第 6 步：再跑完整 debug session

```powershell
agent_workbench.bat session debug
```

### 第 7 步：最后跑 feature session

```powershell
agent_workbench.bat session feature --task agent_workbench\tasks\<your_task>.yaml
```

## 11. 迁移成功的判断标准

至少满足这些：

### 基础层

- `doctor` 通过
- `build` 通过
- `.vscode/tasks.json` 已生成

### 串口层

- `uart exec` 能看到 ready banner
- `uart exec` 能看到 prompt
- `cli_transcript.log` 能记录命令和回应

### session 层

- `session debug` 会生成 `session_summary.md`
- `session feature` 会生成 `feature_summary.md`
- `assertions.jsonl` 中 blackbox 断言通过

## 12. 最常见的迁移问题

## 12.1 `doctor` 报 toolchain 不存在

通常是：

- `tools.cmake.toolchain_file` 写错了

## 12.2 `build` 失败

通常是：

- 新项目还不是 CMake
- build 目录写错
- toolchain 文件写错

## 12.3 `uart exec` 一直失败

优先检查：

- `uart.port`
- `uart.baudrate`
- `uart.ready_banner`
- `uart.prompt`
- 当前串口是否被别的工具占用

## 12.4 手工串口能通，workbench 不通

优先检查：

- ready banner 配置是否写对
- prompt 配置是否写对
- `probe_commands` 是否真的是新项目支持的命令
- 有没有把旧项目的 task 和断言原样搬过来没改

## 12.5 `session feature` 全部 fail

很常见的原因不是代码坏，而是 task 没改干净。

尤其要检查：

- `acceptance.blackbox[].needle`
- `verify.cli_commands`

## 12.6 为什么没有 `cli_diag.json`

如果命令执行成功，通常不会生成失败诊断文件。

这不是 bug，反而是正常现象。

## 13. 给小白的最短迁移清单

如果你只想按最短路径完成迁移，照下面做：

1. 把整个 `agent_workbench/` 目录复制到新项目
2. 把 `agent_workbench.bat` 和 `setup_workbench.bat` 复制到新项目根目录
3. 删掉：
   - `agent_workbench/runtime/`
   - `agent_workbench/evidence/`
   - `agent_workbench/generated/`
   - `__pycache__`
4. 修改 `agent_workbench/agent_workbench.yaml`
5. 修改 `agent_workbench/tasks/*.yaml`
6. 运行：
   - `setup_workbench.bat`
   - `agent_workbench.bat doctor`
   - `agent_workbench.bat init-vscode`
   - `agent_workbench.bat build`
   - `agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status`
7. 能通后，再跑：
   - `agent_workbench.bat session debug`
   - `agent_workbench.bat session feature --task agent_workbench\tasks\<your_task>.yaml`

## 14. 迁移后推荐再做的优化

当基础适配已经成功后，建议继续做这些增强：

1. 把新项目的 CLI 输出固定成稳定的 ready banner 和 prompt
2. 给固件补 `DebugCliStats`
3. 把 task 文件改成真正反映新项目行为的验收标准
4. 把 Continue 模板改成你的项目命令集合
5. 把 monitor 变量项补齐

## 15. 相关文件

- `agent_workbench/README.md`
- `agent_workbench/VS_CODE_CONTINUE_GUIDE_ZH.md`
- `agent_workbench/prompts/continue_agent_zh.md`
- `agent_workbench/examples/portable_migration.md`
