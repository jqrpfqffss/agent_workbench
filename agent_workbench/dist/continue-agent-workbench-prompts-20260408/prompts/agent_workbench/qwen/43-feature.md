```text
这是功能任务。

如果只是验证：
cmd /c ".\agent_workbench.bat verify current --task <TASK>.yaml"

如果明确要求实现：
1. 运行：
   cmd /c ".\agent_workbench.bat context --mode feature --stage implement --task <TASK>.yaml"
2. 只读最新 *_paste.md
3. 只改 allowed_edits
4. 改完后运行：
   cmd /c ".\agent_workbench.bat verify current --task <TASK>.yaml"

最终只输出：
- feature: ...
- scope: ...
- evidence: ...
- validation: ...
- next: ...
```
