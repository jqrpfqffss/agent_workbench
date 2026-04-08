```text
这是一个自动化测试任务。

不要自己组织复杂流程。
请按顺序只运行：

cmd /c ".\agent_workbench.bat test generate --task <TASK>.yaml"
cmd /c ".\agent_workbench.bat test run"

然后优先读取：
- agent_workbench/runtime/unit.log
- agent_workbench/generated/tasks/<TASK_ID>/unit_test_plan.md
- agent_workbench/generated/tasks/<TASK_ID>/blackbox_assertions.yaml
- agent_workbench/generated/tasks/<TASK_ID>/implementation_brief.md

如果测试失败，先判断是：
- task 规格问题
- generated 测试资产问题
- 源码行为问题

最终只输出：
- result: ...
- assets: ...
- first_fail: ...
- next: ...
```
