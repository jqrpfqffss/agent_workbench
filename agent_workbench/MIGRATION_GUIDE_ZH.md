# agent_workbench 迁移指南

这份指南面向第一次把 `agent_workbench` 迁移到新 STM32 项目的人。

目标很简单：把这套自动化控制面复制到新仓库后，只改少量配置，就能继续使用 VS Code + Continue Agent 跑构建、烧录、串口验证、自动调试和自动功能开发流程。

## 1. 应该拷贝什么

最稳妥的方式不是零散挑脚本，而是整体带走下面这些内容。

### 1.1 仓库根目录

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
- `templates/`
- `tests/`
- `README.md`
- `VS_CODE_CONTINUE_GUIDE.md`
- `VS_CODE_CONTINUE_GUIDE_ZH.md`
- `LOW_CONTEXT_MODELS_GUIDE_ZH.md`
- `MIGRATION_GUIDE_ZH.md`
- `CONTINUE_AUTO_MODE_GUIDE_ZH.md`

## 2. 不建议一起迁移的运行产物

下面这些目录属于运行时输出，通常不建议带到新项目里：

- `agent_workbench/runtime/`
- `agent_workbench/evidence/`
- `agent_workbench/generated/`
- `__pycache__/`
- `.continue/rules/`
- `.vscode/tasks.json`

其中 `.continue/rules/` 和 `.vscode/tasks.json` 都应该在新项目里重新生成，而不是手抄旧项目版本。

## 3. 新项目建议满足的前提

### 3.1 优先是 CMake 项目

当前 workbench 的主构建路径基于 CMake，迁移最顺手的状态是：

- 已有 `CMakeLists.txt`
- 已有交叉编译 toolchain 文件
- 可以在命令行独立完成 `cmake configure + build`

### 3.2 最好有稳定的 UART CLI

如果你希望继续使用 `uart exec`、`session debug`、`verify current` 这类自动验证能力，最好具备：

- 稳定的 `ready banner`
- 稳定的 `prompt`
- 1 到 3 条可靠的 smoke 命令

例如：

- `ready banner: MyBoard CLI ready.`
- `prompt: cli>`
- `probe_commands: ["help", "status"]`

### 3.3 本地模型也可以直接迁移

如果你主要使用本地模型，不需要额外改代码，只需要在 `agent_workbench.yaml` 中切换默认 profile，例如：

- `balanced_local`
- `deepseek16k`
- `qwen32k`
- `deepseek_r1`
- `qwen7b`
- `glm`

## 4. 迁移后第一件事：改 `agent_workbench.yaml`

这是整个系统的单一事实来源。迁移后的第一轮修改几乎都集中在这里。

### 4.1 项目基本信息

至少确认这些字段：

- `project.name`
- `project.root`
- `project.build_dir`
- `project.artifact_elf`
- `project.compile_commands`
- `project.source_dirs`

### 4.2 CMake 与工具链

至少确认这些字段：

- `tools.cmake.generator`
- `tools.cmake.build_type`
- `tools.cmake.toolchain_file`
- `tools.cmake.configure_args`
- `tools.cmake.build_args`

### 4.3 烧录与复位

至少确认这些字段：

- `tools.openocd.daemon_cmd`
- `tools.openocd.telnet_port`
- `tools.flash.default_method`
- `tools.flash.methods.*.flash`
- `tools.flash.methods.*.reset`

### 4.4 UART 与诊断串口

至少确认这些字段：

- `uart.port`
- `uart.baudrate`
- `uart.ready_banner`
- `uart.prompt`
- `uart.probe_commands`
- `diag_uart.port`
- `diag_uart.default_hex_requests`

### 4.5 规划器与 Continue 自动模式

迁移到新版 workbench 后，还要确认下面两组配置：

- `planner.templates_dir`
- `planner.max_total_steps`
- `planner.minimum_template_count`
- `continue.rules_dir`
- `continue.rules_template_dir`
- `continue.required_rules`
- `continue.model_rules`

第二阶段完成后，模板库默认应不少于 15 个；当前仓库已经扩展到 16 个模板，覆盖 GPIO、定时器、PWM、ADC、DMA、I2C、SPI、EXTI、UART echo、故障分析等常见任务。

### 4.6 本地模型 profile

至少确认这些字段：

- `agent.default_profile`
- `agent.profiles.balanced_local`
- `agent.profiles.deepseek16k`
- `agent.profiles.qwen32k`
- `agent.profiles.deepseek_r1`
- `agent.profiles.qwen7b`
- `agent.profiles.glm`

## 5. task 文件迁移时怎么改

不要直接照搬旧项目 task 的业务内容。至少要对齐下面这些字段：

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

如果你希望弱模型更稳，建议继续补上 `implementation` 块，例如：

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

- 模型更不容易乱读文件
- 模型更不容易乱改文件
- 自动断言更容易写得稳定

## 6. 迁移后的初始化顺序

建议按下面顺序执行：

```powershell
setup_workbench.bat
agent_workbench.bat doctor
agent_workbench.bat init-vscode
agent_workbench.bat init-continue-rules
```

执行完成后，新仓库里应该出现：

- `.vscode/tasks.json`
- `.continue/rules/stm32_auto_workflow.md`
- `.continue/rules/stm32_weak_model_guard.md`
- `.continue/rules/stm32_powershell_syntax.md`
- `.continue/rules/stm32_error_recovery.md`
- `.continue/rules/stm32_hardware_safety.md`
- `.continue/rules/stm32_model_deepseek_r1.md`
- `.continue/rules/stm32_model_qwen7b.md`
- `.continue/rules/stm32_model_glm.md`

这些 rules 都会根据 `agent_workbench.yaml` 自动注入项目名、UART banner、prompt、默认 profile 等仓库专属信息。

## 7. 迁移后的第一轮验证

### 7.1 项目快照

```powershell
agent_workbench.bat scan-project --json
```

确认能得到结构化快照，包括：

- `source_files`
- `detected_init_functions`
- `planner_templates`
- `planner_template_count`

### 7.2 自动计划能力

```powershell
agent_workbench.bat plan "增加 I2C 传感器寄存器读取" --json
```

确认返回了合理的 `steps[]`，并且步骤里包含读取文件、实现、构建、验证等动作。

### 7.3 规则生成与完整性检查

```powershell
agent_workbench.bat init-continue-rules --json
agent_workbench.bat doctor --json
```

新版 `doctor` 不只检查 rules 是否存在，还会检查：

- rules 目录是否完整
- 多模型 rules 是否齐全
- 自动生成的 rules 是否已绑定当前项目名和 UART 标记
- planner 模板数量是否达到最低要求
- 迁移文档和自动模式文档是否存在关键章节

### 7.4 构建验证

```powershell
agent_workbench.bat build --json
agent_workbench.bat parse-errors --json
```

如果构建失败，`parse-errors --json` 会基于规则库输出结构化错误与 `suggested_fix`。

### 7.5 CLI smoke

```powershell
agent_workbench.bat uart exec --reset-first --expect-ready --command help
```

如果你的新项目 smoke 命令不是 `help`，就改成你自己的 `probe_commands`。

## 8. 迁移后的 Continue 自动模式怎么用

推荐流程如下：

1. 在 Continue Agent 中直接输入一句需求。
2. Continue 先跑 `agent_workbench.bat plan "<需求>" --json`。
3. Continue 按 `steps[]` 读取和修改文件。
4. Continue 通过 `build --json`、`parse-errors --json`、`uart exec --json` 完成闭环。
5. 遇到烧录、复位、硬件动作时再请求确认。

常见示例：

- `给板子加一个 1Hz LED 闪烁`
- `给 STM32 添加 PWM 蜂鸣器控制，频率 1kHz，PA8 引脚`
- `分析为什么 CLI 没有出现 ready banner`

更完整的自动模式说明见 [CONTINUE_AUTO_MODE_GUIDE_ZH.md](CONTINUE_AUTO_MODE_GUIDE_ZH.md)。

## 9. 推荐的迁移验收标准

满足下面这些条件，基本可以视为迁移成功：

1. `agent_workbench.bat doctor --json` 通过，且没有 `fail`
2. `agent_workbench.bat scan-project --json` 能输出结构化项目快照
3. `agent_workbench.bat plan "<需求>" --json` 能生成合理步骤
4. `.continue/rules/` 下能看到 8 个自动模式规则文件
5. `agent_workbench.bat build --json` 正常
6. `agent_workbench.bat uart exec ...` 能生成 `cli_transcript.log`
7. Continue 能按 rules 驱动一次完整的自动执行流程

## 10. 常见坑

### 10.1 不要手抄旧项目的 `.vscode/tasks.json`

正确做法是迁移后重新生成：

```powershell
agent_workbench.bat init-vscode
```

### 10.2 不要手抄旧项目的 `.continue/rules/`

正确做法是迁移后重新生成：

```powershell
agent_workbench.bat init-continue-rules
```

### 10.3 串口号最容易漏改

最常见的是 `uart.port` 或 `diag_uart.port` 没同步到新机器。

### 10.4 `ready_banner` / `prompt` 写错时，很像“串口没通”

如果 `uart exec --expect-ready` 一直失败，先检查配置是否和真实固件输出一致。

### 10.5 task scope 太宽时，弱模型更容易跑偏

尽量缩小 `scope.include`，并补 `implementation.read_candidates` / `edit_candidates`。

## 11. 回归测试建议

迁移完成后，建议再跑一轮回归：

```powershell
py -3.8 -m unittest discover -s agent_workbench/tests -p "test_*.py"
```

当前回归重点覆盖：

- planner 模板库回归
- project scanner 回归
- doctor 规则与文档检查
- VS Code / Continue rules 生成
- 编译错误规则解析

## 12. 继续阅读

- [README.md](README.md)
- [VS_CODE_CONTINUE_GUIDE_ZH.md](VS_CODE_CONTINUE_GUIDE_ZH.md)
- [CONTINUE_AUTO_MODE_GUIDE_ZH.md](CONTINUE_AUTO_MODE_GUIDE_ZH.md)
- [LOW_CONTEXT_MODELS_GUIDE_ZH.md](LOW_CONTEXT_MODELS_GUIDE_ZH.md)
- [prompts/continue_agent_zh.md](prompts/continue_agent_zh.md)
