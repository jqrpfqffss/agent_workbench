```text
这是测试任务。

请按顺序运行：
cmd /c ".\agent_workbench.bat test generate --task <TASK>.yaml"
cmd /c ".\agent_workbench.bat test run"

然后优先读取：
- unit.log
- unit_test_plan.md
- blackbox_assertions.yaml
- implementation_brief.md

最终只输出：
- result: ...
- assets: ...
- failure: ...
- reason: ...
- next: ...
```
