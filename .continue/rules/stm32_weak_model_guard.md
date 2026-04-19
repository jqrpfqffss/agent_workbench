# STM32 弱模型防护规则

这份规则专门给上下文紧、工具调用容易出错的模型使用。
如果你是较弱模型，必须比主规则更保守。

## 首要原则

- 不要炫技。
- 不要自己发明流程。
- 不要缩写命令。
- 不要合并命令。
- 不要隐含执行。
- 不要假设工具会成功。

## 命令格式规则

- 命令前一律写 `cmd /c`
- 路径优先使用 `/`
- 带空格的参数必须包在双引号里
- 每次只执行一条命令
- 优先使用 `--json`
- 不要使用 PowerShell 管道去解析 JSON
- 不要写 `ConvertFrom-Json`
- 不要写 `cd xxx && command`
- 不要写 `command1 ; command2`

## 伪执行防护

每次运行命令前都要先输出:

`下一步执行: <完整命令>`

每次拿到结果后都要输出:

`返回: <JSON 摘要>`

如果你没有真实运行工具:

- 不要说“已执行”
- 不要说“返回如下”
- 不要自己脑补 exit_code
- 不要自己脑补 transcript

## plan 消费规则

- 先看 `template_id`
- 再看 `parameter_extractions`
- 再看 `hardware_context`
- 再看 `steps`
- 最后才看用户原话

弱模型不能忽略结构化字段重新自由发挥。

## edit_file 保守策略

当 step 是 `edit_file` 时:

- 只改当前 step.file
- 只做当前 hint 直接要求的修改
- 不要顺手重构
- 不要顺手改命名
- 不要顺手整理 unrelated code
- 不要顺手删除旧逻辑

## `code_change_hints` 使用策略

- 看到 `add_function` 时，优先按 code_template 建骨架
- 看到 `add_call` 时，只插入调用，不展开更多逻辑
- 看到 `reuse_existing_handle` 时，不新增同名句柄
- 看到 `add_command_table_entry` 时，只改命令表相关位置
- 看到 `review_header_exports` 时，除非确定需要，否则先不改头文件

## build 失败后的动作

顺序必须固定:

1. 看第一条 error
2. 运行 `fix-build --json`
3. 看 `suggested_fixes[0]`
4. 只修第一条
5. 重新 build

## 什么时候必须停止

- 同一个步骤连续失败 3 次
- 总步骤数超过 `plan.constraints.max_total_steps`
- `parameter_extractions` 和用户原话严重冲突
- `hardware_context` 没给出可用映射，且你也无法从代码现状确定
- 修改范围即将超出 `allowed_edit_files`
- 烧录步骤需要确认但用户尚未确认

## 什么时候必须汇报冲突

- 用户指定 PA8，但硬件知识库没有 PA8 的映射
- 用户指定 TIM1，但 snapshot 显示 TIM1 已被其他功能占用
- 用户要求新增命令，但命令名已存在
- build 错误建议修改的文件不在允许列表中

## 输出风格

- 一次说清一个动作
- 少说结论，多给真实结果
- 多用结构化短句
- 不要长篇解释内部推理

## 好的示例

```text
下一步执行: cmd /c ".\agent_workbench.bat plan ""给STM32添加PWM蜂鸣器，1kHz，PA8"" --json"
返回: template_id=timer_pwm, frequency_hz=1000, pin=PA8, recommended=TIM1_CH1
```

```text
下一步执行: cmd /c ".\agent_workbench.bat fix-build --json"
返回: first_fix=add_declaration -> extern TIM_HandleTypeDef htim1;
```

## 坏的示例

- “我已经帮你跑了编译，应该没问题”
- “通常 TIM1 可以这样配，所以我直接改了”
- “我猜你想要 50% 占空比”
- “我把相关文件都顺手整理了一下”

## 弱模型专用收束规则

- 当前步骤完成后，立刻停下来检查下一步
- 不要同时打开过多文件
- 不要并行做两个修复
- 不要把第一条报错和第二条 warning 一起修
- 不要把 plan 里的读文件步骤省略

## 对 PWM 场景的特殊提醒

- 先用 `hardware_context.timer_config`
- 再用 `code_change_hints`
- 不要自己重新算 prescaler/period
- 不要自己换定时器通道
- 不要自己把 PA8 改成别的脚

## 对 CLI 命令场景的特殊提醒

- 先用 `parameter_extractions.cli_command_name`
- 查 `available_cli_commands`
- 已存在就按修改处理
- 不存在再按新增处理
- 保持 `help` 输出风格稳定
- 保持 ready banner 与 prompt 不变

## 低上下文阅读节奏

- 每轮最多优先读 2 到 3 个文件
- 先读 step.file
- 再读与 step.file 最相关的一个头文件或实现文件
- 不要一次性把十几个文件都打开

## 文件修改节奏

- 一次只落一个逻辑块
- 先落句柄或声明
- 再落函数
- 再落调用
- 最后 build

## 弱模型专用检查清单

每次 edit 之前检查:

- 当前文件是否在 allowed_edit_files 中
- 当前 hint 是否已经足够明确
- 是否真的需要新建文件

每次 build 之前检查:

- 是否已经保存刚才的改动
- 是否只处理了当前阻塞错误
- 是否没有顺手改 unrelated 区域

每次 build 之后检查:

- 是否拿到真实 errors
- 是否先看了第一条 error
- 是否需要 fix-build

## 最容易犯的错误

- 漏看 `notes`
- 漏看 `existing_handles`
- 漏看 `available_cli_commands`
- 把 `code_template` 当自然语言描述而不是骨架
- 在没有 confirmation 时先 flash
- 没有真实运行命令却写“返回”

## 必须保留的稳定元素

- ready banner `STM32 UART CLI ready.`
- prompt `cli>`
- help 输出的整体风格
- 现有命令的命名与行为

## 当信息不够时怎么做

- 不要脑补
- 不要替用户假设硬件接法
- 先报告缺口
- 给出你缺的具体字段

## 弱模型的 PWM 操作模板

1. 读 plan
2. 找 `frequency_hz`
3. 找 `pin`
4. 找 `recommended`
5. 找 `prescaler/period/ccr`
6. 按 hints 落代码
7. build
8. fix-build if needed

## 弱模型的 CLI 命令操作模板

1. 读 plan
2. 找 `cli_command_name`
3. 查 `available_cli_commands`
4. 找命令表文件
5. 加 handler 声明
6. 加命令表项
7. 加 handler 实现
8. build
9. uart verify

## 失败时的表达方式

好的表达:

- “第 1 条错误要求先补 `extern TIM_HandleTypeDef htim1;`，我先做这一处最小修复。”
- “plan 没给出可用引脚映射，我先停止，避免猜错硬件。”

坏的表达:

- “我顺便把整个定时器模块重构了”
- “我猜 PA8 大概可以这么配”
- “应该差不多能工作”

## 最后的弱模型停手线

- 当前 step 完成就停
- 当前 build 通过就停
- 当前 fix 已经最小化就停
- 当前信息不足就停并汇报

## 记忆口诀

- 先 plan
- 再读文件
- 再按 hints 改
- 再 build
- 再 fix-build
- 再验证

## 弱模型最终原则

- 保守
- 真实
- 最小
- 可验证
- 可停手
- 可复盘

## 结束语

- 宁可少改，也不要乱改
