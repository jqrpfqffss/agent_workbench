# agent-workbench-feature

## 适用场景

当用户要求：

- 新增一个功能
- 修改一个小功能
- 基于 task 做功能验证
- 改完代码后用 CLI / test / feature session 做闭环验证

时使用本技能。

## 目标

让功能工作遵循统一闭环：

1. 先明确 task
2. 再最小实现
3. 再自动化验证
4. 最后基于 evidence 下结论

## 路径选择

### 1. 用户只想验证当前功能状态

直接运行：

```powershell
cmd /c ".\agent_workbench.bat verify current --task <任务文件.yaml>"
```

### 2. 用户明确要求改代码

先运行：

```powershell
cmd /c ".\agent_workbench.bat context --mode feature --stage implement --task <任务文件.yaml>"
```

然后只读取最新 `*_paste.md`，并严格遵守其中的：

- `allowed_reads`
- `allowed_edits`
- `implementation.max_edit_files`

完成代码后，再运行：

```powershell
cmd /c ".\agent_workbench.bat verify current --task <任务文件.yaml>"
```

必要时才使用显式长流程：

```powershell
cmd /c ".\agent_workbench.bat test generate --task <任务文件.yaml>"
cmd /c ".\agent_workbench.bat test run"
cmd /c ".\agent_workbench.bat session feature --task <任务文件.yaml>"
cmd /c ".\agent_workbench.bat compare --latest"
cmd /c ".\agent_workbench.bat report --latest"
```

## 必读文件

优先读取：

- task yaml
- `implementation_brief.md`
- `direct_verify_summary.md`
- 或最新 `session_verdict.json`
- `feature_summary.md`

## 行为约束

1. 先任务，后实现
2. 先最小修改，再验证
3. 不要扩大改动范围
4. 除非 task 明确要求，否则不要随意改 help 文本、banner、prompt、稳定字符串
5. 如果 evidence 已经能说明当前状态，不要重复长命令链

## 输出要求

按这个顺序输出：

1. `功能结果`
2. `修改范围`
3. `证据链`
4. `验证结果`
5. `下一步`

如需固定模板，使用：

- `templates/feature-report-template.md`

如需闭环说明，读取：

- `references/feature-loop.md`
