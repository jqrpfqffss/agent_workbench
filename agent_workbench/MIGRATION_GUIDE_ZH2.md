# agent_workbench 迁移到其它 STM32 项目的详细教程

这份文档面向这样一种场景：

- 你已经有一个可用的 `agent_workbench`
- 现在想把它迁移到另一个 STM32 工程
- 目标不是“把文件拷过去就算完”，而是迁移后真的能跑 `doctor / build / integration install / uart`

本文尽量把迁移动作拆成可执行步骤，并说明每一步成功时应该看到什么、失败时该先查哪里。

## 1. 迁移成功的标准

一次完整迁移，至少应满足下面几条：

1. `cmd /c ".\agent_workbench.bat doctor --json"` 返回 `fail_count = 0`
2. `cmd /c ".\agent_workbench.bat build --json"` 返回 `exit_code = 0`
3. `cmd /c ".\agent_workbench.bat scan-project --json"` 能扫到目标工程源码，而不是空结果
4. 你需要的 integration 能正常安装并通过检查
5. 如果项目带 UART CLI，`uart exec` 能看到真实的 `ready_banner` 和 `prompt`

只复制目录但达不到上面这些结果，不算迁移完成。

## 2. 目标项目建议满足的前提

为了让 `agent_workbench` 迁移后马上能用，目标 STM32 项目最好满足以下条件：

- 运行环境是 Windows + PowerShell
- 项目已经能在本机通过 CMake 构建
- 最好是 CubeMX/CubeIDE 风格目录，至少常见目录能被 `source_dirs` 覆盖
- 如果项目有板级 CLI，最好已经能通过串口看到稳定的 ready banner 和 prompt
- 如果项目没有 UART CLI，也可以迁移，但要把 `uart.enabled` 改为 `false`
- 如果项目没有独立诊断串口，也可以迁移，但要把 `diag_uart.enabled` 改为 `false`

特别注意：

- 当前 `build` 流程内部调用的是 `cmake -S ... -B ...` 和 `cmake --build ...`
- 也就是说，目标项目如果不是 CMake 工程，`doctor`、`integration install` 仍可用，但 `build / verify` 这条主流程不能直接工作

## 3. 迁移后目标项目里应该有哪些内容

推荐的目录形态如下：

```text
<target-project>/
├─ Core/
├─ Drivers/
├─ cmake/
├─ agent_workbench/
├─ agent_workbench.bat
├─ setup_workbench.bat
├─ AGENTS.md                  # 由 integration install opencode 生成
├─ opencode.json              # 由 integration install opencode 生成
├─ .opencode/                 # 由 integration install opencode 生成
└─ .continue/                 # 由 integration install continue 生成
```

这里有两个重点：

- 手工迁移的核心内容是 `agent_workbench/`、`agent_workbench.bat`、`setup_workbench.bat`
- `AGENTS.md`、`opencode.json`、`.opencode/`、`.continue/` 都属于“生成物”，建议迁移后重新生成，不要把旧项目里的结果直接当最终结果使用

## 4. 第一步：复制哪些文件

### 4.1 必须复制

从源项目复制到目标项目根目录：

- `agent_workbench/`
- `agent_workbench.bat`

### 4.2 推荐一起复制

- `setup_workbench.bat`

它只是一个薄封装，内部会调用 `agent_workbench\bin\setup.bat`。复制它的好处是，迁移后在目标项目根目录可以直接执行：

```powershell
.\setup_workbench.bat
```

### 4.3 建议不要把下面这些旧生成物当成最终状态

- `AGENTS.md`
- `opencode.json`
- `.opencode/`
- `.continue/`

原因是这些文件会包含源项目的实际值，比如：

- 项目名
- 串口 ready banner
- prompt
- 默认 profile
- source dirs

如果直接沿用，很容易出现“文件在，但内容还是旧项目”的假成功。

### 4.4 PowerShell 复制示例

下面是一个最直接的复制方式示例：

```powershell
Copy-Item -Recurse -Force H:\old_project\agent_workbench H:\new_project\
Copy-Item -Force H:\old_project\agent_workbench.bat H:\new_project\
Copy-Item -Force H:\old_project\setup_workbench.bat H:\new_project\
```

### 4.5 可选清理项

如果你希望目标项目更干净，复制后可以手动清理这些“历史运行产物”：

- `agent_workbench/runtime/`
- `agent_workbench/evidence/`
- `agent_workbench/generated/`
- `agent_workbench/__pycache__/`
- `agent_workbench/core/__pycache__/`

这一步不是必须的，但对新项目更清爽。

## 5. 第二步：修改 `agent_workbench/agent_workbench.yaml`

这是迁移里最关键的一步。`agent_workbench.yaml` 是整个 workbench 的单一配置源，构建、烧录、串口、诊断串口、monitor、integration 渲染都会用它。

建议你按下面的顺序检查。

### 5.1 先改项目路径相关字段

最少要确认这些字段：

- `project.name`
- `project.root`
- `project.build_dir`
- `project.artifact_elf`
- `project.compile_commands`
- `project.source_dirs`

常见规则：

- 如果 `agent_workbench/` 仍然放在目标项目根目录下，那么 `project.root` 通常继续写 `..`
- `project.build_dir`、`project.artifact_elf`、`project.compile_commands` 必须彼此一致，全部指向目标项目真实的构建输出
- `project.source_dirs` 至少要覆盖目标项目的主要源码目录

### 5.2 再改构建相关字段

重点检查：

- `tools.cmake.generator`
- `tools.cmake.build_type`
- `tools.cmake.toolchain_file`

如果目标项目不是 `MinGW Makefiles`，就要改成它真实使用的 generator。  
如果 toolchain 文件名和本示例不同，也要改成目标工程真实路径。

### 5.3 再改 OpenOCD / 烧录相关字段

重点检查：

- `tools.openocd.daemon_cmd`
- `tools.flash.default_method`
- `tools.flash.methods.*`

这里最容易踩的坑是 MCU 变了，但 OpenOCD target 脚本没改。

例如：

- F103 工程常见是 `target/stm32f1x.cfg`
- F4 工程就不该继续沿用这个脚本

所以如果你是从 F1 迁到 F4/F7/H7/L4 等别的系列，必须把所有相关 OpenOCD 命令里的 target 脚本一起改掉。

### 5.4 再改 UART CLI 相关字段

如果目标项目有 UART CLI，需要重点确认：

- `uart.enabled`
- `uart.port`
- `uart.baudrate`
- `uart.ready_banner`
- `uart.prompt`
- `uart.probe_commands`

这里不要照搬示例值。  
`ready_banner` 和 `prompt` 必须和目标固件真实输出完全对应。  
`probe_commands` 也必须换成目标固件真正支持的命令，不能继续写旧项目里的 `red on`、`blue on` 之类示例命令。

如果目标项目没有 CLI：

```yaml
uart:
  enabled: false
```

### 5.5 再改 diag UART 相关字段

重点检查：

- `diag_uart.enabled`
- `diag_uart.port`
- `diag_uart.baudrate`
- `diag_uart.default_hex_requests`

当前示例工程里，`diag_uart.default_hex_requests` 用的是把 `help\r\n`、`status\r\n` 写成十六进制后的 ASCII 帧，这是为了在同一个 CLI 口上验证 host 侧诊断工具链。

迁移到真实项目时，通常有三种情况：

1. 目标项目有独立诊断串口，而且你知道真实协议帧  
   这时就把 `default_hex_requests` 改成真实协议报文

2. 目标项目没有独立诊断串口  
   这时把 `diag_uart.enabled` 改成 `false`

3. 你只是临时验证 host 端链路  
   可以暂时让 `diag_uart.port` 指向 CLI 串口，但要明确这只是过渡做法

### 5.6 `monitor.symbols.elf_path` 要和 ELF 一致

即使你暂时不用 monitor，也建议确认：

- `monitor.symbols.elf_path`

它通常应该和 `project.artifact_elf` 指向同一个 ELF。

### 5.7 单元测试命令按需调整

如果目标项目仍沿用 workbench 自带测试，一般不用改。  
如果你有额外 host 侧测试命令，可以检查：

- `checks.unit.enabled`
- `checks.unit.command`

### 5.8 迁移期推荐配置

迁移初期建议：

```yaml
hardware:
  mode: prefer
```

原因是这样即使硬件暂时不在线，很多主机侧步骤仍然能先跑通。  
等你把串口、烧录、reset 都验证稳定后，再考虑切成 `required`。

## 6. 一份可参考的配置片段

下面给一个“迁移到新项目后”的配置片段示例。字段名只是示意，你需要替换成目标工程真实值。

```yaml
project:
  name: motor_ctrl
  root: ..
  build_dir: build/cmake-debug
  artifact_elf: build/cmake-debug/motor_ctrl.elf
  compile_commands: build/cmake-debug/compile_commands.json
  source_dirs:
    - Core
    - Drivers
    - cmake
    - agent_workbench

hardware:
  mode: prefer

tools:
  cmake:
    generator: MinGW Makefiles
    build_type: Debug
    toolchain_file: cmake/arm-none-eabi-toolchain.cmake
  openocd:
    daemon_cmd: openocd -l "{openocd_live_log_posix}" -f interface/stlink.cfg -f target/stm32f4x.cfg -c "gdb_port 3333; tcl_port 6666; telnet_port 4444"
  flash:
    default_method: openocd_cmd
    methods:
      openocd_cmd:
        flash: openocd -f interface/stlink.cfg -f target/stm32f4x.cfg -c "program {artifact_elf_posix} verify reset exit"
        reset: openocd -f interface/stlink.cfg -f target/stm32f4x.cfg -c "init; reset run; shutdown"

uart:
  enabled: true
  port: COM7
  baudrate: 115200
  ready_banner: STM32 UART CLI ready.
  prompt: cli>
  probe_commands:
    - help
    - status

diag_uart:
  enabled: false

monitor:
  enabled: false
  symbols:
    elf_path: build/cmake-debug/motor_ctrl.elf
```

## 7. 第三步：安装依赖

在目标项目根目录执行：

```powershell
.\setup_workbench.bat
```

如果你没有复制这个包装脚本，也可以执行：

```powershell
agent_workbench\bin\setup.bat
```

它会做三件事：

1. 解析并选定 Python
2. 安装 `agent_workbench/requirements.txt` 里的依赖
3. 自动执行 doctor 和 init-vscode

如果这一步失败，优先检查：

- 本机 Python 是否可用
- pip 是否可用
- 依赖是否成功安装了 `PyYAML` 和 `pyserial`

## 8. 第四步：跑基础验证

下面这组命令建议按顺序执行，而且都在目标项目根目录执行。

### 8.1 doctor

```powershell
cmd /c ".\agent_workbench.bat doctor --json"
```

理想结果：

- `exit_code = 0`
- `status = pass`
- `fail_count = 0`

迁移初期常见现象：

- `artifact_elf` 是 `warn`
- `compile_commands` 是 `warn`

这通常意味着你还没 build 过一次，或者路径还没改对。  
如果是 `toolchain_file`、`runtime_root`、`generated_root` 这类变成 `fail`，就必须先修。

### 8.2 build

```powershell
cmd /c ".\agent_workbench.bat build --json"
```

理想结果：

- `exit_code = 0`
- `summary` 里没有 build errors

如果这里失败，优先检查：

- `project.build_dir`
- `project.artifact_elf`
- `tools.cmake.generator`
- `tools.cmake.toolchain_file`

### 8.3 scan-project

```powershell
cmd /c ".\agent_workbench.bat scan-project --json"
```

建议重点看这些字段：

- `project.name`
- `source_dirs`
- `source_file_count`
- `source_files`
- `detected_init_functions`
- `existing_handles`
- `uart.ready_banner`
- `uart.prompt`

如果 `source_file_count` 很小或接近 0，通常是 `project.source_dirs` 没配对。  
如果 UART 字段和你的固件实际输出不一致，后面 `uart exec` 基本也不会成功。

### 8.4 test run

```powershell
cmd /c ".\agent_workbench.bat test run --json"
```

这一步主要验证 host 侧测试链路没被迁移破坏。

## 9. 第五步：安装并检查 integration

### 9.1 先看有哪些 integration

```powershell
cmd /c ".\agent_workbench.bat integration list --json"
```

当前版本至少应能看到：

- `opencode`
- `continue`

### 9.2 安装 OpenCode 集成

```powershell
cmd /c ".\agent_workbench.bat integration install opencode --json"
cmd /c ".\agent_workbench.bat integration check opencode --json"
```

安装后应该生成这些项目级文件：

- `AGENTS.md`
- `opencode.json`
- `.opencode/agent/*.md`
- `.opencode/command/*.md`

注意：

- 老命令 `init-opencode-agents` 仍然能用，但它现在只是兼容入口
- 新项目里推荐统一使用 `integration install opencode`

### 9.3 安装 Continue 集成

```powershell
cmd /c ".\agent_workbench.bat integration install continue --json"
cmd /c ".\agent_workbench.bat integration check continue --json"
```

安装后应生成：

- `.continue/rules/stm32_auto_workflow.md`
- `.continue/rules/stm32_weak_model_guard.md`
- `.continue/rules/stm32_task_cookbook.md`
- 以及其它对应规则文件

### 9.4 什么时候需要重新安装 integration

只要你修改了下面这些配置，建议重新执行一次 integration install：

- `project.name`
- `project.source_dirs`
- `uart.ready_banner`
- `uart.prompt`
- `diag_uart.port`
- `agent.default_profile`

因为这些值会被渲染进 `AGENTS.md`、`opencode.json`、规则文件等生成物里。

## 10. 第六步：做串口和诊断口验证

### 10.1 如果目标项目有 UART CLI

先在板子已上电、固件已烧入且串口已接好的前提下执行：

```powershell
cmd /c ".\agent_workbench.bat uart exec --expect-ready --command help --command status --json"
```

理想结果：

- 能看到 ready banner
- 能看到 prompt
- `help` 和 `status` 返回符合预期

如果目标板只有 reset 后才会重新打印 ready banner，那么在你确认允许硬件 reset 的前提下，再考虑使用带 reset 的流程。

### 10.2 如果目标项目有独立诊断口

```powershell
cmd /c ".\agent_workbench.bat diag exec --json"
```

要点：

- `diag_uart.default_hex_requests` 必须是这个项目真实支持的请求帧
- 如果你沿用了示例工程里那种 `help/status` 的 ASCII 十六进制帧，大概率在真实协议口上会超时或返回乱码

### 10.3 如果目标项目没有这两类串口

可以先禁用它们：

```yaml
uart:
  enabled: false

diag_uart:
  enabled: false
```

这样 workbench 仍然能做 doctor、build、integration、scan-project 等主机侧工作。

## 11. 第七步：开始实际使用

迁移成功后，常见用法如下。

### 11.1 OpenCode

1. 在目标项目根目录启动 OpenCode
2. OpenCode 会读取根目录的 `AGENTS.md`
3. 你可以直接提需求，或使用：
   - `/plan-stm32`
   - `/verify`
   - `/fix-build`
   - `/uart-smoke`
   - `/flash-reset`

### 11.2 Continue

1. 在 IDE 里启用项目规则
2. 确保 `.continue/rules/` 已生成
3. 让模型优先通过 `cmd /c ".\agent_workbench.bat ... --json"` 触发标准工作流

## 12. 常见问题与修复建议

### 12.1 `toolchain_file` 失败

原因通常是：

- `tools.cmake.toolchain_file` 路径没改
- 目标项目的 toolchain 文件名和源项目不同

先修这个，再看 build。

### 12.2 `artifact_elf` 和 `compile_commands` 一直是 warn

常见原因：

- 还没 build 过
- `project.build_dir` 改了，但 `artifact_elf` 和 `compile_commands` 还指向旧目录

这三个字段必须联动。

### 12.3 `scan-project` 扫到的源码很少

通常是：

- `project.source_dirs` 没包含真实源码目录

如果目标工程不是 `Core/Drivers/cmake` 这种结构，就必须按实际目录改。

### 12.4 `uart exec` 找不到 ready banner 或 prompt

通常是：

- `uart.port` 错了
- `uart.baudrate` 错了
- `uart.ready_banner` 和固件真实输出不一致
- `uart.prompt` 和固件真实输出不一致
- `probe_commands` 里写了目标固件不支持的命令

### 12.5 `diag exec` 一直超时

通常是：

- `diag_uart.port` 错了
- `default_hex_requests` 没换成真实项目协议
- 实际项目没有独立诊断口，却还沿用了示例配置

### 12.6 OpenOCD 命令能跑，但就是连不上板

优先检查：

- target 脚本是否仍是旧 MCU 系列
- `default_method` 是否选对
- 板子是否真的是 ST-Link + OpenOCD 这条路径

### 12.7 生成了 `AGENTS.md`，但内容还是旧项目信息

说明你很可能：

- 没先改 `agent_workbench.yaml`
- 或改完后没重新执行 `integration install opencode`

生成物不是自动跟随配置变化的，改完配置要重新生成。

### 12.8 `pyserial` 缺失但 doctor 只是 warn

这通常表示：

- 基本的 PowerShell fallback 还能用
- 但交互式串口体验仍不完整

想要最稳妥，还是建议把 `setup_workbench.bat` 跑通。

## 13. 推荐的迁移顺序清单

如果你只想按顺序照着做，可以直接用下面这份清单：

1. 复制 `agent_workbench/`、`agent_workbench.bat`、`setup_workbench.bat`
2. 修改 `agent_workbench/agent_workbench.yaml`
3. 执行 `.\setup_workbench.bat`
4. 执行 `cmd /c ".\agent_workbench.bat doctor --json"`
5. 执行 `cmd /c ".\agent_workbench.bat build --json"`
6. 执行 `cmd /c ".\agent_workbench.bat scan-project --json"`
7. 执行 `cmd /c ".\agent_workbench.bat test run --json"`
8. 执行 `cmd /c ".\agent_workbench.bat integration install opencode --json"`
9. 执行 `cmd /c ".\agent_workbench.bat integration check opencode --json"`
10. 按需执行 `cmd /c ".\agent_workbench.bat integration install continue --json"`
11. 按需执行 UART 或 diag UART 验证

做到这一步后，再开始真实开发，会比“边迁移边猜”稳得多。

## 14. 附加说明

### 14.1 关于旧命令

以下旧入口仍可用，但更推荐新入口：

- `init-opencode-agents`  
  推荐替换为 `integration install opencode`

### 14.2 关于历史文档

如果你需要查以前的迁移方案或历史设计说明，可以去：

- `agent_workbench/docs/history/`

### 14.3 关于简版说明

如果你只想看最短版迁移步骤，可以配合阅读：

- `agent_workbench/examples/portable_migration.md`
