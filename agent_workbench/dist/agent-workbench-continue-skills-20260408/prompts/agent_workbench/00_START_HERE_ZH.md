# Continue Prompt Pack For agent_workbench

这套模板是给 Continue Agent 模式直接复制使用的。

选择方式：

1. 当前就是这个 `serial` 项目，想最快验证是否跑通
   打开：`01_CURRENT_PROJECT_VERIFY_SERIAL.md`

2. 你使用的是 DeepSeek 本地模型
   打开：`deepseek/`

3. 你使用的是 Qwen 本地模型
   打开：`qwen/`

4. 你使用的是别的模型，或想要更通用的模板
   打开：`common/`

5. 你想把一个大任务拆成 analyze / implement / verify 多轮
   打开：`02_LOW_CONTEXT_STAGE_RULES.md`

使用规则：

1. 一次只复制一个模板给 Continue
2. 不要把多个模板拼在一起
3. 如果模板里有 `<task.yaml>`，请替换成实际 task 文件
4. 如果 Continue 已经开始乱跑，不要继续纠错对话
5. 直接开一个新会话，重新贴更短的模板

优先级建议：

1. 只想看当前项目是否通过：`01_CURRENT_PROJECT_VERIFY_SERIAL.md`
2. 想做自动化调试：`common/02_DEBUG_AUTOMATION.md`
3. 想做自动化测试：`common/03_TEST_AUTOMATION.md`
4. 想做功能开发和验证：`common/04_FEATURE_AUTOMATION.md`

对本地模型的建议：

1. DeepSeek：优先用 `deepseek/`，最短、最硬约束
2. Qwen：优先用 `qwen/`，比通用模板更稳
3. 如果一轮输出开始变长或跑偏，立即改用更短模板
