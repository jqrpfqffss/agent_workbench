# STM32 Task Cookbook

这份手册给 Continue 一个“结构化 plan 如何展开为代码动作”的速查表。
它不是替代主规则。
它是主规则的实例库。

## 用法

- 先运行 `plan`
- 找到 `template_id`
- 对照本手册找到最近的任务类型
- 再按示例展开 `code_change_hints`

## 示例 1: PWM 蜂鸣器

用户输入:

`给 STM32 添加 PWM 蜂鸣器控制，频率 1kHz，PA8 引脚，占空比 50%`

预期关键字段:

- `template_id = timer_pwm`
- `parameter_extractions.frequency_hz = 1000`
- `parameter_extractions.pin = PA8`
- `parameter_extractions.duty_percent = 50`
- `hardware_context.pin_mapping.recommended = TIM1_CH1`
- `hardware_context.timer_config.prescaler = 71`
- `hardware_context.timer_config.period = 999`
- `hardware_context.timer_config.ccr = 500`

典型代码展开:

- 读 `Core/Src/main.c`
- 读 `Core/Inc/main.h`
- 在 `USER CODE BEGIN PV` 附近添加或复用 `htim1`
- 在 `USER CODE BEGIN PFP` 添加 `MX_TIM1_PWM_Init` 原型
- 在 `USER CODE BEGIN 4` 添加 PWM 初始化函数
- 在 `USER CODE BEGIN 2` 添加调用
- build
- fix-build if needed
- flash after confirmation
- uart verify

## 示例 2: LED 闪烁

用户输入:

`给板子加一个 1Hz LED 闪烁`

预期关注字段:

- `template_id = gpio_blink`
- `parameter_extractions.period_ms` 可能为空
- 如果 period 没提取到，可以保守使用 1000ms
- 优先查 `main.c` 的主循环与现有 LED 引脚

典型代码展开:

- 在 `main.c` 中找 LED 定义和 `while (1)` 循环
- 只添加最小计时逻辑
- 不改 CLI 栈
- 保持 ready banner 与 prompt

## 示例 3: 新增 CLI 命令

用户输入:

`添加一个 CLI 命令 uptime 显示系统运行时间`

预期关键字段:

- `template_id = uart_cli_command`
- `parameter_extractions.cli_command_name = uptime`

展开顺序:

- 读 `Core/Src/cli.c`
- 读 `Core/Src/app_cli_commands.c`
- 读 `Core/Inc/app_cli_commands.h`
- 在命令表里找到插入点
- 新增 handler 前置声明
- 新增命令表条目
- 新增 handler 实现
- build
- uart verify

如果 snapshot 显示 `uptime` 已存在:

- 不新增重复命令
- 改为增强现有实现

## 示例 4: ADC 采样

用户输入:

`增加 ADC 电压采样并上报`

关注点:

- `template_id = adc_read`
- 如果 plan 没给明确 ADC 通道，不要乱猜物理脚位
- 先读已有 ADC 初始化与使用方式
- 先做最小可编译实现

## 示例 5: 定时器中断

用户输入:

`增加一个 100ms 的定时中断任务`

关注点:

- `template_id = timer_basic` 或 `interrupt_handler`
- 如果 `hardware_context` 给了定时参数，直接使用
- 如果没有，先看现有定时器是否已存在
- 避免与已存在的 UART、CLI 初始化冲突

## 示例 6: GPIO 输出控制

用户输入:

`增加 GPIO 输出控制继电器`

关注点:

- `template_id = gpio_output`
- 优先确认目标引脚是否已在 `main.h` 定义
- 如果没有结构化 pin，不要自行假定某个脚
- 尽量只改 `main.c`/`main.h`

## 示例 7: SPI 设备

用户输入:

`增加 SPI Flash 读写接口`

关注点:

- `template_id = spi_device`
- 先找已有 SPI 初始化
- 如果已有 `hspi1`，优先复用
- 如果没有，不要跨很多文件大改，先做最小闭环

## 示例 8: I2C 设备

用户输入:

`增加 I2C 传感器寄存器读取`

关注点:

- `template_id = i2c_device`
- 先看已有 `hi2c*`
- 如果已有句柄，复用
- 如果没有明确从机地址，不要伪造具体值

## 示例 9: build 失败修复

场景:

`build --json` 返回 error

正确动作:

1. 读取 `errors[0]`
2. 运行 `fix-build --json`
3. 看 `suggested_fixes[0].fix`
4. 只修第一条
5. 重新 build

错误动作:

- 同时改三处
- 一边修 error 一边清 warning
- 不看 `fix-build` 直接凭印象大改

## 示例 10: UART 回归验证

场景:

改完功能后执行:

`cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json"`

通过标准:

- `exit_code == 0`
- transcript 中有 `{ready_banner}`
- transcript 中有 `{prompt}`
- `help` 和 `status` 没有明显回归

## 从 hints 到代码的翻译规则

### `add_private_variable`

含义:

- 在用户变量区加一个变量

不要做:

- 把它加在随机位置
- 改动已有同名变量

### `add_function_prototype`

含义:

- 在函数原型区补声明

不要做:

- 把完整函数体放进头文件

### `add_function`

含义:

- 新增函数骨架

要做:

- 优先复用 `code_template`
- 用 `parameter_hints` 填具体值

### `add_call`

含义:

- 在初始化或主流程中插入调用

要做:

- 保持插入点尽量靠近 plan 指定区域

### `add_command_table_entry`

含义:

- 在 CLI 命令表里新增或更新条目

要做:

- 保持现有格式
- 保持 help 输出风格一致

## 最终提醒

- 先结构化，后改代码
- 先最小闭环，后扩展功能
- 先保证可编译，再追求完整
- 先保住 CLI 与启动提示，再做新功能

## 示例 11: GPIO 输入

用户输入:

`增加一个 GPIO 输入检测按键状态`

展开建议:

- 先确认目标引脚是否明确
- 如果 pin 不明确，不要擅自选脚
- 优先在 `main.c` 与 `main.h` 内完成最小闭环

## 示例 12: UART echo

用户输入:

`增加一个串口 echo 回显命令`

展开建议:

- 通常匹配 `uart_echo`
- 先看现有 CLI 命令风格
- 保持一进一出的简单语义
- build 后必须做 UART 回归验证

## 示例 13: 故障分析

用户输入:

`分析 hardfault 崩溃原因`

展开建议:

- 通常匹配 `fault_diagnosis`
- 先收集报错上下文
- 再读故障相关文件
- 不要一上来就改很多代码

## 示例 14: fix-build 单独使用

场景:

用户已经手动 build 过一次，
你只需要拿结构化修复建议。

命令:

`cmd /c ".\agent_workbench.bat fix-build --json"`

正确输出关注点:

- `suggested_fixes[0].error_code`
- `suggested_fixes[0].fix.action_type`
- `suggested_fixes[0].fix.code`

## 示例 15: 已有句柄复用

场景:

plan notes 提示:

`htim1 已存在，建议复用现有句柄而不是重复声明。`

正确动作:

- 不要再写 `TIM_HandleTypeDef htim1;`
- 只改初始化逻辑或新增调用

## 示例 16: 已有命令增强

场景:

plan notes 提示:

`CLI 命令 uptime 已存在，此次应视为修改/增强而不是新增。`

正确动作:

- 不再新增第二个 uptime
- 找到已有实现
- 做最小增强

## 一份通用验收清单

- plan 是否先执行
- parameter_extractions 是否被使用
- hardware_context 是否被使用
- code_change_hints 是否被使用
- build 是否通过
- fix-build 是否在需要时调用
- flash 是否在确认后执行
- uart verify 是否通过

## cookbook 的核心理念

- 不是为了替代模型思考
- 是为了减少模型重新发明流程
- 是为了让弱模型也能稳定走通
- 是为了让强模型不要无谓发散

## 一句话总结

- 让 Continue 少猜
- 让 plan 多说
- 让修改更小
