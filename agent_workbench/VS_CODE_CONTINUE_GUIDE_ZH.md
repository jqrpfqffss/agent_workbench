# VS Code 配合 Continue 使用教程

这份教程面向当前仓库的优化版 `agent_workbench`。

目标很简单：

- 让你在 VS Code 里用 Continue `Agent` 模式时，不再手工拆任务
- 让本地模型先自动拆成小任务，再按 `analyze -> implement -> verify` 顺序推进
- 让每一步都落到 `agent_workbench` 的 evidence 文件里，最后能基于证据下结论

## 1. 先理解现在的推荐入口

当前最推荐的入口不是直接给 Continue 一大段长提示词，而是：

1. 用户只给一句自然语言任务
2. Continue 第一动作运行 `autoflow`
3. `agent_workbench` 自动起草 task、自动拆解 subtasks、自动生成当前阶段卡
4. Continue 只执行这一轮的 `current_subtasks`
5. 阶段切换后，继续跑 `autoflow --resume`

一句话理解：

`autoflow` 负责“先把路铺好”，Continue 负责“沿着当前这小段路走完”。

## 2. 一次性准备

在项目根目录打开 VS Code 后，先做一次基础准备：

```powershell
cmd /c ".\setup_workbench.bat"
cmd /c ".\agent_workbench.bat doctor"
cmd /c ".\agent_workbench.bat init-vscode"
cmd /c ".\agent_workbench.bat build"
```

如果这些都正常，你会得到：

- [.vscode/tasks.json](/h:/stm32_RAG/code/serial/.vscode/tasks.json)
- [doctor_report.md](/h:/stm32_RAG/code/serial/agent_workbench/runtime/doctor_report.md)
- `agent_workbench/runtime/continue/` 下的运行时提示文件

## 3. 最推荐的使用方式

### 3.1 用户只给一句任务

例如：

```text
你现在在当前 STM32 HAL + agent_workbench 项目中工作，请一次性完成“使用 TIM3 定时器让 RED LED(PB0) 以约 1 Hz 闪烁”的功能，并完成自动化验证。
```

### 3.2 Continue 第一动作固定这样做

不要先读一堆大文件，不要先写长篇分析，先运行：

```powershell
cmd /c ".\agent_workbench.bat autoflow --goal ""你现在在当前 STM32 HAL + agent_workbench 项目中工作，请一次性完成“使用 TIM3 定时器让 RED LED(PB0) 以约 1 Hz 闪烁”的功能，并完成自动化验证。"""
```

运行完成后，先打开：

- [autoflow_start.md](/h:/stm32_RAG/code/serial/agent_workbench/runtime/autoflow_start.md)

这个文件是当前整个自动流的总控卡。

## 4. `autoflow` 实际帮你做了什么

执行 `autoflow --goal ...` 后，workbench 会自动完成这些动作：

1. 推断任务类型
2. 生成临时 task 草稿
3. 规范化 task 字段
4. 自动拆成小任务
5. 生成当前阶段的 context pack
6. 写入状态文件，告诉 Continue 现在该做哪一步

关键输出文件通常在这里：

- [autoflow_state.json](/h:/stm32_RAG/code/serial/agent_workbench/runtime/autoflow_state.json)
- [autoflow_start.md](/h:/stm32_RAG/code/serial/agent_workbench/runtime/autoflow_start.md)
- `agent_workbench/generated/requests/<request>/task_draft.yaml`
- `agent_workbench/generated/tasks/<task_id>/task_breakdown.md`
- `agent_workbench/runtime/context_pack_*_paste.md`

## 5. Continue 每一轮到底该怎么做

### 第 1 轮：Analyze

先看：

- `autoflow_start.md` 里 `Read First` 指向的 `*_paste.md`

Continue 在这一轮只做：

- 读取当前阶段卡
- 完成 `current_subtasks`
- 使用 `agent_workbench.bat` 跑卡片里要求的命令
- 不越级做 implement 或 verify 的事

### 第 2 轮：Implement

当上一轮的 `next_commands` 指向新的 `context` 阶段时，先运行：

```powershell
cmd /c ".\agent_workbench.bat autoflow --resume"
```

然后重新打开：

- [autoflow_start.md](/h:/stm32_RAG/code/serial/agent_workbench/runtime/autoflow_start.md)

这时 `current_stage` 会切到 `implement`，`current_subtasks` 也会更新。

Continue 在这一轮只做：

- 只改允许修改的文件
- 做最小实现
- 跑本地构建和必要回归

### 第 3 轮：Verify

再次运行：

```powershell
cmd /c ".\agent_workbench.bat autoflow --resume"
```

重新读取新的阶段卡。

Continue 在这一轮只做：

- 运行验证命令
- 读取最新 evidence
- 输出结论

### 纯 CLI 操作的例外

如果用户的任务本身就是现有 CLI 直接能完成的动作，比如：

- 点亮红灯
- 关闭绿灯
- 查询状态

那么 `autoflow` 现在会自动把它识别成“verify-only”任务：

- 不要求改代码
- `task_breakdown.md` 会跳过 `implement`
- `autoflow_start.md` 会直接把下一阶段指到 `verify`
- verify 阶段卡会给出精确 UART 命令，例如：
  - `cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command ""red on"" --command ""status"""`

这类任务里，Continue 不应该再去发明 `workflow`、`observe`、`monitor` 或额外代码修改。

## 6. 你在 VS Code 里点哪些任务

打开 `Terminal -> Run Task`，优先使用这些任务：

- `Agent Workbench: Doctor`
- `Agent Workbench: Build`
- `Agent Workbench: Autoflow From Current Goal`
- `Agent Workbench: Autoflow Resume`
- `Agent Workbench: Report Latest Verdict`

如果你要做当前项目的串口直接验证，也可以用：

- `Agent Workbench: Direct Verify (CLI Regression)`

## 7. Continue 最短使用姿势

如果你想让 Continue 少出错，推荐直接把下面这段贴给 Continue `Agent`：

```text
如果用户给的是自然语言任务，请不要自己拆流程，不要先读大文件。第一动作固定运行：
cmd /c ".\agent_workbench.bat autoflow --goal ""<用户原始需求>"""

命令完成后先读取：
agent_workbench/runtime/autoflow_start.md

然后严格遵守：
1. 只读取当前阶段卡
2. 只完成 current_subtasks
3. 只通过 agent_workbench.bat 执行自动化动作
4. 阶段切换后先运行：
   cmd /c ".\agent_workbench.bat autoflow --resume"
5. 如果命令失败、evidence 缺失、或 manual_checks_pending=true，就停止并基于 evidence 说明原因
```

仓库里现成的中文版提示词在这里：

- [continue_autoflow_zh.md](/h:/stm32_RAG/code/serial/agent_workbench/prompts/continue_autoflow_zh.md)
- [continue_start_zh.md](/h:/stm32_RAG/code/serial/agent_workbench/prompts/continue_start_zh.md)

## 8. 当前项目的直接验证怎么做

如果你现在不是要新增功能，而是只想快速验证当前项目状态，直接运行：

```powershell
cmd /c ".\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml"
```

然后看：

- [direct_verify_summary.md](/h:/stm32_RAG/code/serial/agent_workbench/runtime/direct_verify_summary.md)

这是最快的“当前项目健康检查”路径。

## 9. 什么时候看哪些 evidence

### 调试串口握手问题时优先看

- [cli_transcript.log](/h:/stm32_RAG/code/serial/agent_workbench/runtime/cli_transcript.log)
- [cli_diag.json](/h:/stm32_RAG/code/serial/agent_workbench/runtime/cli_diag.json)

重点关注这些分类：

- `rx_zero`
- `parser_no_command`
- `tx_or_host_rx`
- `ready_missing`
- `prompt_missing`

### 看一轮 session 总结时优先看

- `session_verdict.json`
- `session_brief.md`
- `session_summary.md`
- `feature_summary.md`
- `assertions.jsonl`
- `compare_brief.md`

### 看任务是否已经拆好时优先看

- `task_breakdown.md`
- `autoflow_state.json`
- 当前阶段的 `*_paste.md`

## 10. `autoflow_state.json` 怎么看

这个文件很关键，它相当于当前自动流的状态机。

重点字段：

- `goal`: 原始目标
- `task_path`: 当前自动生成的 task 草稿
- `stage`: 当前阶段
- `current_subtasks`: 当前这一轮只需要完成的子任务
- `next_stage`: 下一阶段
- `next_commands`: 下一步应该运行的命令
- `stop_conditions`: 什么情况下必须停下来

只要 Continue 跟着这个文件走，成功率会比让它自由发挥高很多。

## 11. 适合本地模型的工作方式

如果你在 Continue 里用的是 DeepSeek / Qwen 之类本地模型，推荐这样做：

1. 每次只让它处理一个阶段
2. 每一轮只喂它一个 `*_paste.md`
3. 阶段切换后重新 `autoflow --resume`
4. 不要把 README、task、summary、源码一次性全塞进去

如果想切默认预算档位，改：

- [agent_workbench.yaml](/h:/stm32_RAG/code/serial/agent_workbench/agent_workbench.yaml)

把 `agent.default_profile` 调成：

- `balanced_local`
- `deepseek16k`
- `qwen32k`

## 12. 迁移到其它项目时怎么用

迁移后，最少只需要改两类东西：

1. [agent_workbench.yaml](/h:/stm32_RAG/code/serial/agent_workbench/agent_workbench.yaml)
2. `agent_workbench/tasks/*.yaml`

如果新项目还没有 task，也没关系。现在可以直接先用：

```powershell
cmd /c ".\agent_workbench.bat autoflow --goal ""<用户原始任务>"""
```

先让 workbench 自动起草 task，再继续跑。

更完整的迁移说明见：

- [MIGRATION_GUIDE_ZH.md](/h:/stm32_RAG/code/serial/agent_workbench/MIGRATION_GUIDE_ZH.md)

## 13. 最容易踩的坑

### 坑 1：让 Continue 自己拼 shell 命令

不要让它写：

```powershell
cd ... && ...
```

推荐统一使用：

```powershell
cmd /c ".\agent_workbench.bat <subcommand>"
```

另外，`uart` 现在兼容一些模型常写错的格式，例如下面这些也能被 workbench 自动纠正：

```powershell
.\agent_workbench\bin\agent_workbench.bat uart --exec "red on"
.\agent_workbench\bin\agent_workbench.bat uart --status
```

### 坑 2：一开始就让它读很多文件

不要一上来就塞：

- README
- guide
- task
- summary
- 多个源码文件

优先只给：

- `autoflow_start.md`
- 当前阶段的 `*_paste.md`

### 坑 3：让模型同时做 analyze + implement + verify

这会让本地模型很容易跑偏。

正确做法是按阶段推进，每轮只做一件事。

### 坑 4：没有 evidence 就宣布完成

没有新的 evidence，就不要认定任务完成。

## 14. 给小白的最短路线

如果你就想马上开始，直接照下面做：

1. 在 VS Code 打开项目根目录
2. 运行 `Agent Workbench: Autoflow From Current Goal`
3. 输入你的自然语言任务
4. 打开 [autoflow_start.md](/h:/stm32_RAG/code/serial/agent_workbench/runtime/autoflow_start.md)
5. 把它指向的 `*_paste.md` 贴给 Continue Agent
6. Continue 做完当前阶段后，运行 `Agent Workbench: Autoflow Resume`
7. 重复直到进入 `verify`
8. 最后基于 evidence 看结论

## 15. 推荐继续看的文件

- [README.md](/h:/stm32_RAG/code/serial/agent_workbench/README.md)
- [continue_start_zh.md](/h:/stm32_RAG/code/serial/agent_workbench/prompts/continue_start_zh.md)
- [continue_autoflow_zh.md](/h:/stm32_RAG/code/serial/agent_workbench/prompts/continue_autoflow_zh.md)
- [continue_low_context_zh.md](/h:/stm32_RAG/code/serial/agent_workbench/prompts/continue_low_context_zh.md)
- [LOW_CONTEXT_MODELS_GUIDE_ZH.md](/h:/stm32_RAG/code/serial/agent_workbench/LOW_CONTEXT_MODELS_GUIDE_ZH.md)
- [MIGRATION_GUIDE_ZH.md](/h:/stm32_RAG/code/serial/agent_workbench/MIGRATION_GUIDE_ZH.md)
