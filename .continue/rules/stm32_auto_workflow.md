# STM32 Agent Workbench 自动执行主规则

你正在为项目 `serial` 工作。
你运行在 Continue 的 Agent 模式中。
所有 LLM 推理都发生在 Continue 内部。
`agent_workbench` 只是一个纯确定性的工具层。
你必须把它输出的结构化 JSON 当作权威输入。

## 项目绑定信息

- 项目名: `serial`
- 构建目录: `H:\stm32_RAG\code\serial\build\cmake-debug`
- 主要源码目录: `Core, Drivers, cmake, agent_workbench`
- UART 端口: `COM3`
- 诊断口端口: `COM3`
- 默认 profile: `balanced_local`
- ready banner: `STM32 UART CLI ready.`
- prompt: `cli>`

## 角色定位

- 你负责读用户自然语言需求。
- 你负责调用 `agent_workbench.bat`。
- 你负责根据结构化 JSON 做代码决策。
- 你负责使用 Continue 的读写文件能力真正改代码。
- 你负责在失败时重试，但只能按规则重试。
- 你不能把 `agent_workbench` 当成会思考的系统。
- 你不能假设 workbench 会自动写代码。
- 你不能把用户重新拉回手工复制粘贴流程。

## 最重要的工作流总则

1. 收到需求后，永远先运行 `plan`。
2. 只在看到 `plan` JSON 之后，才允许读文件或改文件。
3. `plan.parameter_extractions` 是用户意图的结构化翻译。
4. `plan.hardware_context` 是硬件约束和静态知识库的展开结果。
5. `plan.steps` 是推荐执行顺序。
6. `plan.steps[*].code_change_hints` 是把结构化意图翻译成代码骨架的关键字段。
7. `build --json` 失败时，要先看 `errors[0]`。
8. 如果需要结构化修复建议，要调用 `fix-build --json`。
9. `fix-build` 只负责产出修复建议，不会替你改代码。
10. 所有 shell 命令都要一条一条执行。

## PowerShell 执行规则

- 一律使用 `cmd /c ".\agent_workbench.bat ..."` 这种格式。
- 不要使用 `cd xxx; command`。
- 不要使用 `&&`。
- 不要使用 `;`。
- 不要把多条命令串在一行。
- 路径优先使用 `/` 风格的仓库相对路径。
- 所有支持 JSON 的命令优先加 `--json`。
- 如果你使用 `ps-exec`，它仍然是单条命令，不是脚本执行器。

## 绝对禁止的行为

- 不要跳过 `plan`。
- 不要在没读 `plan` 的情况下直接修改 `Core/Src/main.c`。
- 不要在没看到真实工具返回前说“我已经执行了”。
- 不要基于猜测伪造命令输出。
- 不要超出 `plan.constraints.allowed_edit_files` 的范围修改。
- 不要删除已有 CLI 命令。
- 不要修改 ready banner `STM32 UART CLI ready.`。
- 不要修改 prompt `cli>`。
- 不要修改 `Drivers/` 目录，除非 plan 明确允许。
- 不要为了省事把多个步骤折叠成一句“已完成”。

## 第一步: 先生成计划

收到用户自然语言需求之后，第一件事必须是:

`cmd /c ".\agent_workbench.bat plan ""<用户原话>"" --json"`

你要从返回 JSON 里至少读取这些字段:

- `template_id`
- `parameter_extractions`
- `hardware_context`
- `notes`
- `context.related_files`
- `context.existing_handles`
- `context.user_code_regions`
- `steps`
- `constraints`

## 如何理解 `parameter_extractions`

- 这是 workbench 用 regex 从自然语言中提取的结构化参数。
- 这比重新从用户原话猜一遍更可靠。
- 如果字段有值，优先使用这个值。
- 如果字段为空，再从用户原话里补充判断。
- 常见字段包括:
- `frequency_hz`
- `duty_percent`
- `period_ms`
- `pin`
- `timer`
- `gpio_port`
- `cli_command_name`
- `baud_rate`
- `voltage`

### 例子: PWM

如果 `parameter_extractions` 里有:

- `frequency_hz = 1000`
- `pin = "PA8"`
- `duty_percent = 50`

那么你不需要再自己猜:

- 频率是不是 1kHz
- 引脚是不是 PA8
- 默认占空比是多少

你应把这些值直接用于代码生成和修复判断。

### 例子: CLI 命令

如果 `parameter_extractions.cli_command_name == "uptime"`，
那么你应该把 `uptime` 当成命令名，
而不是重新从整句自然语言里猜一个相近词。

## 如何理解 `hardware_context`

- `hardware_context` 来自静态硬件知识库和项目扫描器。
- 这是 Continue 的硬件事实表，不是建议文本。
- 其中的值优先级高于你的常识推断。

重点子字段:

- `clock`
- `pin_mapping`
- `timer_config`
- `user_code_regions`
- `existing_handles`
- `available_cli_commands`

### `pin_mapping`

如果存在:

- `requested_pin`
- `candidates`
- `recommended`
- `alternate_function_mode`

则优先使用 `recommended`。
不要绕开它自己选另一个定时器通道，除非用户明确要求。

### `timer_config`

如果存在:

- `timer`
- `channel`
- `handle_name`
- `prescaler`
- `period`
- `ccr`
- `target_frequency_hz`

则这些值就是 PWM 或定时器方案的权威参数。
你应尽量把自己的代码修改压缩为“套用这些值”。
不要再次自行计算出不同的 Prescaler/Period。

### `user_code_regions`

如果 plan 或 snapshot 提供了 `user_code_regions`，
优先把新增代码放在对应的 `USER CODE BEGIN/END` 区域内。
如果某个 hint 已经给了目标区域，优先使用 hint 的区域。
如果没有，就从 `user_code_regions` 里找最匹配的位置。

## 如何理解 `notes`

- `notes` 是确定性扫描后得到的风险提示。
- 这些提示需要影响你的代码策略。

例如:

- `htim1 已存在` 时，不要重复声明 `TIM_HandleTypeDef htim1;`
- `CLI 命令 uptime 已存在` 时，把这次任务视为修改或增强，而不是新增
- `未找到该引脚映射` 时，应该向用户报告并停止盲改

## 如何执行 `steps`

你必须严格按 `steps` 顺序执行。
不要自行重排。
不要跳步。

### `action_type = read_file`

你要:

- 读取 `step.file`
- 重点观察 `step.why`
- 只收集与当前 plan 有关的信息
- 在聊天中回报:
- `已读取 <文件>`

### `action_type = edit_file`

你要:

- 仅修改 `step.file`
- 基于 `step.instructions` 和 `step.code_change_hints` 落代码
- 如果 `code_change_hints` 存在，优先按 hints 展开实现
- 不要忽略 hints 改成完全不同的实现方式

### `action_type = create_file`

你要:

- 创建 `step.file`
- 仍然优先依据 `code_change_hints`
- 只创建当前需求直接需要的最小文件

### `action_type = shell`

你要:

- 运行 `step.command`
- 解析 JSON 输出
- 检查 `success_criteria`
- 如果失败，再查看 `on_failure`

## 如何使用 `code_change_hints`

这是本轮规则的核心。
`code_change_hints` 不是参考信息，而是结构化代码操作建议。

每个 hint 可能包含:

- `type`
- `target_region`
- `function_name`
- `code_template`
- `parameter_hints`
- `reason`
- `replace_existing`

### 常见 `type`

- `add_private_variable`
- `reuse_existing_handle`
- `add_function_prototype`
- `add_function`
- `add_call`
- `add_extern_declaration`
- `add_forward_declaration`
- `add_command_table_entry`
- `review_header_exports`
- `apply_structured_request`

### 处理规则

- `add_private_variable`: 在私有变量区添加变量，除非已有同名定义
- `reuse_existing_handle`: 不新增句柄，改为复用并调整原有初始化
- `add_function_prototype`: 把函数声明加到函数原型区
- `add_function`: 新增一个完整函数骨架，再填入必要细节
- `add_call`: 在初始化区加入调用
- `add_extern_declaration`: 在头文件 extern 区补声明
- `add_command_table_entry`: 在命令表里插入或更新项
- `review_header_exports`: 只有确实需要额外头文件导出时才改

## 当 `build --json` 失败时怎么做

你必须按这个顺序处理:

1. 看 `errors[0]`
2. 不要同时处理多条报错
3. 如果 `step.on_failure.retry_command` 存在，运行它
4. 读取 `fix-build` 的 `suggested_fixes`
5. 根据 `suggested_fixes[0].fix` 落具体代码
6. 重新运行当前 build 步骤

## 如何消费 `fix-build --json`

`fix-build` 返回:

- `suggested_fixes[*].error_code`
- `suggested_fixes[*].message`
- `suggested_fixes[*].fix.action_type`
- `suggested_fixes[*].fix.target_files`
- `suggested_fixes[*].fix.target_region`
- `suggested_fixes[*].fix.code_template`
- `suggested_fixes[*].fix.code`
- `suggested_fixes[*].fix.parameter_hints`

### 规则

- 如果 `action_type == add_declaration`，按 `target_files` 和 `code` 精确落位
- 如果 `action_type == add_include`，优先改当前报错文件顶部
- 如果 `action_type == add_definition`，在最合理的源文件中添加定义
- 如果 `action_type == inspect_context`，先读 `context_lines` 再决定最小改动

## 烧录与硬件动作

- 如果某个 shell step 标记了 `requires_confirmation = true`
- 先明确告诉用户即将执行什么
- 等用户确认后再烧录
- 不要默认替用户操作硬件

## 验证动作

对 UART CLI 验证步骤，至少要确认:

- 返回 exit_code 为 0
- transcript 中包含 ready banner
- transcript 中包含 prompt
- help/status 等基础命令未被破坏

如果 transcript 缺少 ready banner:

- 优先怀疑初始化被破坏
- 其次怀疑你改动了稳定字符串
- 再考虑板子复位问题

## 最终报告格式

所有步骤完成后，输出一个清晰的完成报告。
至少包含:

- 用户需求
- 关键参数理解
- 采用的硬件方案
- 修改的文件
- 编译结果
- 烧录结果
- CLI 验证结果
- 证据文件路径

## 报告示例

```text
## 任务完成报告
- 用户需求: 给 STM32 添加 PWM 蜂鸣器控制，频率 1kHz，PA8 引脚
- 理解参数: frequency=1000Hz, pin=PA8, duty=50%
- 硬件方案: TIM1_CH1, prescaler=71, period=999, ccr=500
- 修改的文件: Core/Src/main.c, Core/Inc/main.h
- 编译结果: pass
- 烧录结果: skipped
- CLI 验证结果: pass
- 证据文件:
  - agent_workbench/runtime/build.log
  - agent_workbench/runtime/cli_transcript.log
```

## 快速命令手册

- `cmd /c ".\agent_workbench.bat plan ""<需求>"" --json"`
- `cmd /c ".\agent_workbench.bat scan-project --json"`
- `cmd /c ".\agent_workbench.bat build --json"`
- `cmd /c ".\agent_workbench.bat parse-errors --json"`
- `cmd /c ".\agent_workbench.bat fix-build --json"`
- `cmd /c ".\agent_workbench.bat flash --json"`
- `cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json"`

## 收尾规则

- 如果任务完成，就给报告，不要继续发散修改
- 如果遇到阻断风险，就停在最小安全点并汇报
- 如果 plan 与代码现状冲突，优先尊重实际代码与 snapshot
- 如果 snapshot、parameter_extractions、hardware_context 三者一致，就按它们执行
- 如果它们不一致，先解释冲突，再做最保守的动作

## 字段优先级裁决表

当多个来源同时给出信息时，按下面的优先级使用:

1. `step.code_change_hints`
2. `hardware_context`
3. `parameter_extractions`
4. `notes`
5. `context.user_code_regions`
6. 用户原话
7. 你自己的通用常识

### 说明

- `code_change_hints` 最接近可执行修改。
- `hardware_context` 最接近硬件事实。
- `parameter_extractions` 最接近用户意图。
- 用户原话仍然重要，但优先用于补足空字段，而不是覆盖结构化输出。

## 结构化字段冲突时的处理

### 情况 1: `parameter_extractions` 有值，`hardware_context` 为空

- 继续执行
- 但要谨慎
- 先读相关文件确认现状
- 如果依然无法确定硬件落点，停止并汇报

### 情况 2: `parameter_extractions.pin` 与 `hardware_context.pin_mapping.requested_pin` 不一致

- 先检查 plan 是否包含 notes
- 如果 notes 没解释这个冲突，不要盲改
- 在聊天里点明冲突
- 只在冲突被解释清楚后继续

### 情况 3: `notes` 提示句柄已存在，但 hints 还在要求新增声明

- 以 `notes` 和 snapshot 为准
- 把新增句柄的动作降级为复用现有句柄
- 不要新增重复定义

### 情况 4: `fix-build` 建议修改的文件不在 `allowed_edit_files`

- 不要直接越界修改
- 先向用户汇报受限点
- 如果只是头文件 extern 声明这类小改动，也要先说明原因

## 读文件的最小充分原则

- 只读与当前 step 直接相关的文件
- 如果 `context.related_files` 已经足够，不要扩大阅读范围
- 如果需要额外读文件，要先说明理由
- 如果只是为了找插入点，优先读 `main.c`、`main.h`、相关 CLI 文件

### 推荐阅读顺序

- 功能类任务: `main.c` -> `main.h` -> 功能相关源文件
- CLI 类任务: `cli.c` -> `app_cli_commands.c` -> `app_cli_commands.h`
- 中断类任务: `main.c` -> `stm32f1xx_it.c` -> `stm32f1xx_it.h`
- 调试类任务: 出错文件 -> 对应头文件 -> `main.c`

## 修改代码时的最小充分原则

- 不要顺手统一代码风格
- 不要顺手加 unrelated comment
- 不要顺手清理已有 warning
- 不要顺手移动函数位置，除非 hint 明确要求
- 不要扩大修改范围去“做得更优雅”

## 常见 shell 结果分流

### build

- `exit_code == 0`: 进入下一步
- `exit_code != 0`: 先看 `errors[0]`，再 `fix-build`

### flash

- `exit_code == 0`: 记录为 pass
- `exit_code != 0`: 不要无限重试，先确认是否是硬件连接问题

### uart exec

- `exit_code == 0`: 检查 transcript 是否含 ready banner 与 prompt
- `exit_code != 0`: 优先看 diagnosis 和 transcript

### scan-project

- 如果 source_files 很少，怀疑 source_dirs 配置不完整
- 如果没有 user_code_regions，怀疑当前项目不是 CubeMX 风格

## `add_function` 展开细则

当 hint 类型是 `add_function` 时:

- 先把 `code_template` 整体落到目标区域
- 再只替换与当前请求相关的参数
- 不要把骨架函数完全改写成别的结构
- 不要把函数拆到 hint 没指定的文件

### 对 PWM `add_function` 的额外要求

- 保持 `HAL_TIM_PWM_Init`
- 保持 `HAL_TIM_PWM_ConfigChannel`
- 保持 `HAL_TIM_PWM_Start`
- 优先使用 `timer_config` 给出的值

### 对 CLI `add_function` 的额外要求

- 保持 handler 函数签名风格一致
- 优先使用 `Cli_Printf` / `Cli_WriteString`
- 不要破坏命令表与 help 输出格式

## 什么时候要重新读取文件

- build 错误指向你还没读过的文件
- fix-build 指定了新的 target_files
- notes 提示现有资源冲突，需要确认原实现

如果只是新增一个 extern 声明，
通常不需要把整个项目再重读一遍。

## 什么时候不要重新读取文件

- 只是因为你不确定自己的改动是否正确
- 只是想做更大范围的重构
- 只是想顺便修别的模块

## 典型失败恢复样板

### 样板 A: undeclared handle

1. build 失败
2. `errors[0].message` 含 undeclared
3. 运行 `fix-build --json`
4. 按 `fix.code` 加 extern 声明
5. 重新 build

### 样板 B: unknown type name

1. build 失败
2. `errors[0].message` 含 unknown type name
3. 运行 `fix-build --json`
4. 按 `fix.action_type = add_include` 落 include
5. 重新 build

### 样板 C: undefined reference

1. build 失败
2. `errors[0].message` 含 undefined reference
3. 判断是缺函数定义还是漏编译单元
4. 优先补最小定义
5. 再 build

## stop 条件

遇到下面任一情况，停止并汇报:

- 连续 3 次 build 仍然失败
- 硬件知识库没有对应映射
- 需要越界修改文件
- 烧录前用户没有确认
- UART 回归表明 ready banner 或 prompt 被破坏
- 你无法明确解释当前改动为何安全

## 每一步都要自检

在进入下一步前，自问:

- 当前 step 是否真的完成
- 我是否拿到了真实工具输出
- 我是否误改了 allowed_edit_files 之外的文件
- 我是否保住了稳定字符串
- 我是否只修了第一条阻塞错误

## 面向真实仓库的提醒

- 这个仓库已经有 CLI 与 LED 逻辑
- 不要把示例里的骨架当成必须与现状完全一致
- 应该把结构化 plan 当成“最小可落地意图”
- 然后结合现有实现做细节对齐
