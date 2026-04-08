# agent_workbench 迁移指南

这份文档是给第一次迁移 `agent_workbench` 的人写的。

目标是让你把它迁移到另一个 STM32 项目后，只做少量适配，就能继续用 VS Code + Continue Agent 跑自动化调试、自动化测试、自动化功能验证。

## 1. 迁移时要带哪些文件

最稳妥的方式不是挑着拷几个脚本，而是把下面这些整体带过去。

### 1.1 项目根目录

- `agent_workbench.bat`
- `setup_workbench.bat`

### 1.2 `agent_workbench/` 目录

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
- `LOW_CONTEXT_MODELS_GUIDE_ZH.md`
- `MIGRATION_GUIDE_ZH.md`

## 2. 哪些东西不要带历史垃圾

下面这些目录是运行产物，不建议带到新项目里：

- `agent_workbench/runtime/`
- `agent_workbench/evidence/`
- `agent_workbench/generated/`
- `__pycache__/`

如果你是整个目录复制过去，也没关系。复制后删掉这些运行产物即可。

## 3. 新项目最好满足什么前提

### 3.1 最推荐是 CMake 项目

当前 workbench 的构建主路径是 CMake。

所以最推荐的新项目状态是：

- 已有 `CMakeLists.txt`
- 已有交叉编译 toolchain 文件
- 能在命令行里独立完成 `cmake configure + build`

### 3.2 最好有稳定的 UART CLI

如果你要做 CLI 自动化验证，最好有：

- 稳定的 `ready banner`
- 稳定的 `prompt`
- 稳定的 smoke 命令

例如：

- `ready banner: MyBoard CLI ready.`
- `prompt: cli>`

### 3.3 如果你只用本地模型

没有问题。

迁移后只要在 `agent_workbench.yaml` 里把 `agent.default_profile` 改成：

- `deepseek16k`
- 或 `qwen32k`

VS Code 任务会自动跟随这个默认 profile，不需要你再去改 `.vscode/tasks.json`。

## 4. 迁移后的第一件事：改 `agent_workbench.yaml`

这是最重要的文件。

后面几乎所有动作都依赖它。

### 4.1 项目信息

你至少要改这些：

- `project.name`
- `project.build_dir`
- `project.artifact_elf`
- `project.compile_commands`
- `project.source_dirs`

### 4.2 CMake 与工具链

你至少要确认这些：

- `tools.cmake.generator`
- `tools.cmake.build_type`
- `tools.cmake.toolchain_file`
- `tools.cmake.configure_args`
- `tools.cmake.build_args`

### 4.3 烧录与复位

你至少要确认这些：

- `tools.openocd.daemon_cmd`
- `tools.openocd.telnet_port`
- `tools.flash.default_method`
- `tools.flash.methods.*.flash`
- `tools.flash.methods.*.reset`

### 4.4 UART

你至少要确认这些：

- `uart.port`
- `uart.baudrate`
- `uart.ready_banner`
- `uart.prompt`
- `uart.probe_commands`
- `uart.help_rows`

### 4.5 本地模型 profile

你至少要确认这些：

- `agent.default_profile`
- `agent.profiles.balanced_local`
- `agent.profiles.deepseek16k`
- `agent.profiles.qwen32k`

如果你的新项目只用 DeepSeek 或 Qwen，本质上只需要把 `default_profile` 指过去。

## 5. task 文件要怎么改

你不应该直接沿用旧项目 task 的业务内容。

最少要改这些字段：

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

## 6. 强烈推荐补 `implementation` 块

为了让小上下文、高幻觉模型更稳，建议每个 feature task 都补：

```yaml
implementation:
  read_candidates:
    - Core/Src/cli.c
    - Core/Src/app_cli_commands.c
  edit_candidates:
    - Core/Src/app_cli_commands.c
  stable_strings:
    - "FW version: demo 1.0.0"
  max_edit_files: 1
```

这样做的好处是：

- Continue 不容易乱读文件
- Continue 不容易乱改文件
- 输出更稳定，自动断言更容易写

如果你不写，workbench 也会从 `scope.include` 和 `observability.notes` 里自动推导默认值。

## 7. 迁移后第一轮验证怎么跑

### 7.1 一次性准备

```powershell
setup_workbench.bat
agent_workbench.bat doctor
agent_workbench.bat init-vscode
```

### 7.2 构建验证

```powershell
agent_workbench.bat build
```

### 7.3 生成本地模型阶段卡

```powershell
agent_workbench.bat context --mode debug --stage analyze
```

如果这一步成功，说明新的状态机和 profile 基本已经接上。

### 7.4 CLI smoke

```powershell
agent_workbench.bat uart exec --reset-first --expect-ready --command help
```

如果你项目的 smoke 命令不是 `help`，就改成你自己的 `probe_commands`。

### 7.5 debug session

```powershell
agent_workbench.bat session debug
agent_workbench.bat compare --latest
agent_workbench.bat report --latest
```

### 7.6 feature session

```powershell
agent_workbench.bat test generate --task agent_workbench\tasks\<TASK>.yaml
agent_workbench.bat test run
agent_workbench.bat session feature --task agent_workbench\tasks\<TASK>.yaml
agent_workbench.bat compare --latest
agent_workbench.bat report --latest
```

## 8. 迁移后 VS Code + Continue 怎么用

迁移完成后，优先这样用：

1. 运行一个 `Context Pack` 任务
2. 打开 `agent_workbench/runtime/` 下最新的 `*_paste.md`
3. 整段粘给 Continue Agent
4. 一轮只做一个阶段

## 9. 最常改的地方其实只有这些

如果新项目结构正常，通常真的只需要改：

1. `agent_workbench.yaml`
2. `tasks/*.yaml`
3. 必要时改 `ready_banner / prompt / probe_commands`
4. 必要时改 `default_profile`

其它核心 Python 代码一般不需要改。

## 10. 常见坑

### 10.1 `.vscode/tasks.json` 不要手抄旧项目的

正确做法是迁移后重新执行：

```powershell
agent_workbench.bat init-vscode
```

### 10.2 COM 口错误

最常见的是 `uart.port` 没改。

### 10.3 烧录器 target cfg 错误

芯片变了以后，`tools.openocd.daemon_cmd` 和 `flash.methods.openocd_cmd.*` 往往也要改。

### 10.4 `ready_banner` / `prompt` 写错

这会让 `uart exec --expect-ready` 看起来像“串口没通”，其实只是配置不匹配。

### 10.5 旧 task scope 太宽

如果 `scope.include` 一口气塞了很多文件，小模型会更容易跑偏。尽量把 task scope 缩小。

## 11. 迁移完成后的验收标准

满足下面这些，就说明迁移基本成功了：

1. `doctor` 能通过
2. `build` 能通过
3. `context --mode debug --stage analyze` 能生成阶段卡
4. VS Code 里能看到新的 `Agent Workbench: Context Pack ...` 任务
5. Continue 能直接消费最新 `*_paste.md`
6. `uart exec` 能生成 `cli_transcript.log`
7. `session debug` 或 `session feature` 能生成 `session_verdict.json`、`session_brief.md`、`session_summary.md`

## 12. 继续阅读

- [README.md](README.md)
- [VS_CODE_CONTINUE_GUIDE_ZH.md](VS_CODE_CONTINUE_GUIDE_ZH.md)
- [LOW_CONTEXT_MODELS_GUIDE_ZH.md](LOW_CONTEXT_MODELS_GUIDE_ZH.md)
- [prompts/continue_agent_zh.md](prompts/continue_agent_zh.md)
