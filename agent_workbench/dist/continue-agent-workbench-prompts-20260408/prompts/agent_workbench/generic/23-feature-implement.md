```text
这是一个功能实现任务。

先不要自己通读整个项目。
请先运行：

cmd /c ".\agent_workbench.bat context --mode feature --stage implement --task <TASK>.yaml"

然后只读取最新的：
- *_paste.md
- *_constraints.json
- *_facts.json

必须遵守：
1. 只改 allowed_edits
2. 不扩 scope
3. 不顺手重构
4. 改动完成后不要自己发散验证

改动完成后只输出：
- changed: ...
- files: ...
- risk: ...
- next: run verify current
```
