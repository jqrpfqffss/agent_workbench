# 通用自动化工作流与证据规则

## 一、常用工作流

### 当前状态一键验证

```powershell
cmd /c ".\agent_workbench.bat verify current --task <任务文件.yaml>"
```

适用：

- 用户只想知道当前项目是否通过
- 用户不要求改代码
- 想用最短路径得到结论

### 分阶段低上下文工作流

```powershell
cmd /c ".\agent_workbench.bat context --mode <debug|feature|test> --stage analyze --task <任务文件.yaml>"
cmd /c ".\agent_workbench.bat context --mode <debug|feature|test> --stage implement --task <任务文件.yaml>"
cmd /c ".\agent_workbench.bat context --mode <debug|feature|test> --stage verify --task <任务文件.yaml>"
cmd /c ".\agent_workbench.bat context --stage resume"
```

适用：

- 本地模型上下文小
- 任务需要多轮推进
- 需要强约束模型只做一件事

## 二、证据判断规则

### 当前验证优先看

- `agent_workbench/runtime/direct_verify_summary.md`
- `agent_workbench/runtime/direct_verify_summary.json`

### 如果进入 session，再看

- `session_verdict.json`
- `session_brief.md`
- `session_summary.md`
- `feature_summary.md`
- `assertions.jsonl`
- `cli_transcript.log`
- `cli_diag.json`

## 三、典型失败层级

按这个顺序定位：

1. `doctor`
2. `build`
3. `test_run`
4. `flash/reset`
5. `uart_smoke`
6. `feature_session`

谁先失败，就先报告谁。

## 四、常见误区

1. 一开始就读一堆大文件
2. 在 PowerShell 里直接运行裸 `.bat`
3. 把环境问题误报成代码问题
4. 没有读 evidence 就开始改代码
5. 本来只需要 `verify current`，却手写很长的命令链
