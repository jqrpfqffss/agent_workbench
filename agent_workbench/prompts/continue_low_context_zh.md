# Continue 低上下文阶段模板

这份模板用于 DeepSeek-R1 / Qwen 这类本地模型。

默认规则：

1. 如果用户给的是自然语言目标，第一动作固定是运行：

```powershell
cmd /c ".\agent_workbench.bat autoflow --goal ""<用户原始需求>"""
```

2. 先打开 [autoflow_start.md](../runtime/autoflow_start.md)。
3. 只读取当前阶段的 `*_paste.md`、`task_breakdown.md` 和 task draft。
4. 一轮只做当前 `current_subtasks`。
5. 阶段推进后，固定运行：

```powershell
cmd /c ".\agent_workbench.bat autoflow --resume"
```

6. 只有遇到真实阻塞、非零退出码、或 `manual_checks_pending=true` 才停下。

可直接粘贴给 Continue 的最短模板：

```text
你现在在当前 STM32 HAL + agent_workbench 项目中工作。
如果用户给的是自然语言目标，不要自己规划长流程。
第一动作固定运行：
cmd /c ".\agent_workbench.bat autoflow --goal ""<用户原始需求>"""

然后先读：
- agent_workbench/runtime/autoflow_start.md

之后严格遵守：
1. 只完成当前阶段的 current_subtasks
2. 只使用 agent_workbench.bat 做自动化动作
3. 不要额外读大文件
4. 每次阶段切换后都运行：
   cmd /c ".\agent_workbench.bat autoflow --resume"
5. 只基于最新 evidence 下结论
```
