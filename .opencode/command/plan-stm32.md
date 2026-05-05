---
description: 兼容入口：从自然语言需求生成 STM32 参数探索建议，不作为复杂任务默认主流程
argument-hint: <用户需求描述>
---

# /plan-stm32

这是兼容入口，不是复杂功能开发、自动调试、测试设计的默认流程。复杂任务优先使用四个 skill、`scan-project`、runtime evidence、verify/report/compare 证据闭环。

运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat plan "$ARGUMENTS" --json
```

如果 bat 入口失败，改用：

```powershell
python ".\agent_workbench\workbench.py" plan "$ARGUMENTS" --json
```

只用摘要形式展示返回 JSON，不要把它当成必须执行的主计划。后续是否执行由当前 workflow skill 和 evidence 决定。
