```text
如果用户没有明确要求改代码，只做验证：

cmd /c ".\agent_workbench.bat verify current --task <TASK>.yaml"

如果用户明确要求改代码：
1. 运行：
   cmd /c ".\agent_workbench.bat context --mode feature --stage implement --task <TASK>.yaml"
2. 只读最新 *_paste.md
3. 只改 allowed_edits
4. 改完后运行：
   cmd /c ".\agent_workbench.bat verify current --task <TASK>.yaml"

输出只允许：
- feature: ...
- scope: ...
- evidence: ...
- next: ...
```
