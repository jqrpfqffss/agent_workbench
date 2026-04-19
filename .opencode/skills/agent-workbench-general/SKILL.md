# agent-workbench-general

## 适用场景

当仓库中存在 `agent_workbench/agent_workbench.yaml`，并且用户希望使用 `agent_workbench` 完成以下任一工作时使用本技能：

- 自动化调试
- 自动化测试
- 自动化功能验证
- 面向任务的通用自动化闭环

如果当前请求已经明确是“串口调试”“测试生成/执行”“功能实现/验证”，优先切换到对应专用技能；如果当前只是总控、分流、选路径、做闭环总览，则使用本技能。

## 核心目标

把模型的默认行为约束成：

1. 优先用 `agent_workbench.bat`，而不是自己拼零散命令
2. 优先看证据，再分析，再决定是否改代码
3. 优先选择最短闭环，减少 PowerShell 命令错误和上下文浪费
4. 对 DeepSeek / Qwen 这类本地模型保持短输入、短输出、强约束

## 第一步怎么做

先做这三件事：

1. 确认项目根目录存在：
   - `agent_workbench/agent_workbench.yaml`
   - `agent_workbench/tasks/`
2. 确认当前任务使用哪个 task yaml
3. 判断当前目标是：
   - 直接验证当前状态
   - 分阶段调试/实现/验证

## PowerShell 必须遵守的命令规则

在 PowerShell 中，批处理入口必须这样调用：

```powershell
cmd /c ".\agent_workbench.bat <子命令> ..."
```

禁止使用这些形式：

```powershell
cd h:\path && agent_workbench.bat doctor
agent_workbench.bat doctor
cd h:\path; agent_workbench.bat doctor
```

原因：

- PowerShell 对 `&&`、裸 `.bat`、多段链式命令的容错差
- 这类错误会浪费大量上下文
- 本技能默认假设当前工作目录已经是仓库根目录

## 默认优先路径

### 1. 只想快速知道“当前项目是否通过”

优先运行：

```powershell
cmd /c ".\agent_workbench.bat verify current --task <任务文件.yaml>"
```

然后优先读取：

- `agent_workbench/runtime/direct_verify_summary.md`
- `agent_workbench/runtime/direct_verify_summary.json`

### 2. 任务较复杂，需要分阶段推进

使用阶段卡：

```powershell
cmd /c ".\agent_workbench.bat context --mode <debug|feature|test> --stage <analyze|implement|verify|resume> --task <任务文件.yaml>"
```

然后只读取：

- `agent_workbench/runtime/` 下最新的 `*_paste.md`

不要一开始就读 README、大量源码、大量历史 session。

## 证据优先级

默认按这个顺序读取：

1. `direct_verify_summary.md`
2. `direct_verify_summary.json`
3. `session_verdict.json`
4. `session_brief.md`
5. `session_summary.md`
6. `feature_summary.md`
7. `assertions.jsonl`
8. `cli_transcript.log`
9. `cli_diag.json`
10. `compare_brief.md`
11. `compare_vs_*.md`

## 行为约束

1. 如果 `doctor`、`build`、`test run` 失败，先停在该层，不要继续推断后面的代码问题
2. 如果串口、烧录器、板子、COM 口不可用，明确归类为环境阻塞，而不是源码故障
3. 如果 evidence 没有给出结论，不要脑补
4. 如果用户没有明确要求改代码，不要主动进入实现阶段
5. 一轮尽量只做一件事，避免混做“分析 + 改代码 + 验证”

## 输出要求

默认输出 4 个部分：

1. `结果`
2. `证据链`
3. `失败层级`
4. `下一步`

如果需要具体格式，使用：

- `templates/general-output-template.md`

如果需要完整工作流说明，读取：

- `references/workflow-and-evidence.md`
