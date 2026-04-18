# Continue Autoflow 中文提示词

把下面整段直接粘贴给 Continue Agent：

```text
你现在在当前 STM32 HAL + agent_workbench 项目中工作。
如果用户给的是一句自然语言任务，请不要自己拆流程，不要先读大文件，不要先写长分析。

第一动作固定运行：
cmd /c ".\agent_workbench.bat autoflow --goal ""<用户原始需求>"""

命令完成后，先读取：
- agent_workbench/runtime/autoflow_start.md

然后严格执行：
1. 只读取 autoflow_start.md 指向的当前阶段卡
2. 只完成 current_subtasks
3. 只使用 agent_workbench.bat 执行自动化动作
4. 当前阶段完成后，如果 next_commands 里切到了下一个 context 阶段，立刻运行：
   cmd /c ".\agent_workbench.bat autoflow --resume"
   然后重新读取 agent_workbench/runtime/autoflow_start.md
5. 如果任何命令非零退出、或出现 manual_checks_pending=true、或 evidence 缺失，就停止并基于 evidence 说明阻塞原因
6. 没有新的 evidence 时，不要声称任务已完成

最终输出必须按下面结构：
1. 当前结果：pass / fail / blocked / needs_review
2. 当前阶段：analyze / implement / verify
3. 已完成的 subtasks
4. 证据链
5. 下一步
```
