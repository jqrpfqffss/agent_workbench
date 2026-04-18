# Continue 中文启动词

这是一份给 Continue `Agent` 模式直接复制粘贴使用的启动词。

适用场景：

- 你希望 Continue 收到自然语言任务后，先自动拆解，再按阶段推进
- 你不想手工告诉它先 `decompose`、再 `context`、再 `build`
- 你希望它优先走 `agent_workbench`，而不是自己乱拼命令

把下面整段直接贴给 Continue：

```text
你现在在当前 STM32 HAL + agent_workbench 项目中工作。

如果用户给的是自然语言任务，请不要自己拆流程，不要先读很多大文件，不要先写长篇分析。第一动作固定运行：

cmd /c ".\agent_workbench.bat autoflow --goal ""<用户原始需求>"""

命令完成后，先读取：
- agent_workbench/runtime/autoflow_start.md

然后严格遵守下面规则：
1. 只读取 autoflow_start.md 指向的当前阶段卡，不要额外扩读大文件。
2. 只完成 current_subtasks，不要跨阶段提前做 implement 或 verify 的事情。
3. 所有自动化动作只通过 agent_workbench.bat 执行，不要自己拼接 cd、&&、; 或零散 cmake/openocd/python 命令。
4. 只运行当前阶段卡里明确列出的 next_commands，不要臆造 workflow、observe、monitor、clean 等未出现的命令。
5. 如果 next_commands 指向下一阶段的 context 卡，先运行：
   cmd /c ".\agent_workbench.bat autoflow --resume"
   然后重新读取 agent_workbench/runtime/autoflow_start.md。
6. 如果任务是现有 CLI 直接可完成的操作，允许跳过 implement 阶段，直接执行 verify 阶段卡里的 UART 命令。
7. 如果任何命令失败、evidence 缺失、或出现 manual_checks_pending=true，就停止并基于 evidence 说明阻塞原因，不要假装任务已经完成。
8. 没有新的 evidence，不要声称 pass。
9. 如果只是验证当前项目，不做新功能、不改代码，优先运行：
   cmd /c ".\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml"

最终输出请固定使用这个结构：
1. 当前结果：pass / fail / blocked / needs_review
2. 当前阶段：analyze / implement / verify
3. 已完成的 subtasks
4. 证据链：列出你实际读取的 evidence 文件
5. 下一步：唯一推荐动作
```

## 当前项目专用版

如果你现在就在这个 `serial` 项目里工作，也可以直接把下面这段贴给 Continue：

```text
你现在在当前 STM32 HAL + agent_workbench 项目中工作。

如果用户给的是自然语言开发或调试任务，第一动作固定运行：
cmd /c ".\agent_workbench.bat autoflow --goal ""<用户原始需求>"""

如果用户只是要求“验证当前项目是否正常”，不要改代码，直接运行：
cmd /c ".\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml"

命令完成后先读：
- agent_workbench/runtime/autoflow_start.md
或
- agent_workbench/runtime/direct_verify_summary.md

然后只基于当前阶段卡或 summary 以及引用到的 evidence 文件行动，不要自行扩展流程。
```

## 使用建议

- 开发新功能：用上面的通用版
- 排查问题：也用通用版，让它先进 `autoflow`
- 只做健康检查：直接用 `verify current`
