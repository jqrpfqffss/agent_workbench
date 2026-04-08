# VS Code 配合 Continue Agent 使用教程

这份教程的目标很直接：让你打开 VS Code 后，几乎不需要自己拼提示词，就能用 `agent_workbench` 跑通自动化调试、自动化测试、自动化功能验证。

## 1. 你会用到什么

仓库里已经准备好的入口有：

- `agent_workbench.bat`
- `setup_workbench.bat`
- `agent_workbench/agent_workbench.yaml`
- `agent_workbench/tasks/*.yaml`
- `agent_workbench/prompts/continue_agent_zh.md`
- `agent_workbench/prompts/continue_low_context_zh.md`
- `.vscode/tasks.json`

唯一长期配置源是：

- `agent_workbench/agent_workbench.yaml`

## 2. 一次性准备

在 VS Code 打开项目根目录后，先跑：

```powershell
setup_workbench.bat
agent_workbench.bat doctor
agent_workbench.bat init-vscode
agent_workbench.bat build
```

这一步做完后，你会得到：

- `.vscode/tasks.json`
- `agent_workbench/runtime/continue/*.md`
- 当前环境检查结果 `agent_workbench/runtime/doctor_report.md`

## 3. VS Code 里怎么点

在 VS Code 里打开：

`Terminal -> Run Task`

你会看到这些关键任务：

- `Agent Workbench: Doctor`
- `Agent Workbench: Build`
- `Agent Workbench: Context Pack (Debug Analyze)`
- `Agent Workbench: Context Pack (Feature Implement)`
- `Agent Workbench: Context Pack (Feature Verify)`
- `Agent Workbench: Context Pack (Test Analyze)`
- `Agent Workbench: Resume Latest Local-Model Task`
- `Agent Workbench: Test Generate (CLI Regression)`
- `Agent Workbench: Test Run`
- `Agent Workbench: UART CLI Smoke`
- `Agent Workbench: Debug Session`
- `Agent Workbench: Feature Session (CLI Regression)`
- `Agent Workbench: Compare Latest`
- `Agent Workbench: Report Latest Verdict`

这些 `Context Pack` 任务会自动使用 `agent_workbench.yaml` 里的 `agent.default_profile`。

如果你现在只想要“当前项目立刻直接验证”，优先用：

- `Agent Workbench: Direct Verify (CLI Regression)`

## 4. Continue Agent 的正确用法

### 4.1 大原则

不要再让 Continue 一上来读一堆大文件。

现在的推荐做法是：

1. 先运行一个 `Context Pack` 任务
2. 打开 `agent_workbench/runtime/` 下最新的 `*_paste.md`
3. 把这个 `*_paste.md` 整段粘给 Continue Agent
4. 让它只做当前阶段

### 4.2 你真正要粘的是什么

优先级从高到低：

1. 当前阶段刚生成的 `*_paste.md`
2. 如果你想看原理，再看同名的 `*_brief.md`
3. 如果你想核对约束，再看 `*_constraints.json`

大多数情况下，直接粘 `*_paste.md` 就够了。

## 5. 调试场景怎么走

### 第一步：生成分析卡

运行：

```powershell
agent_workbench.bat context --mode debug --stage analyze
```

### 第二步：把最新 `*_paste.md` 粘给 Continue

这一轮只要求 Continue：

- 读阶段卡
- 分析 evidence
- 给出根因排序
- 给出唯一下一步

这一轮不要改代码。

### 第三步：如果需要实板验证

运行：

```powershell
agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status
agent_workbench.bat session debug
agent_workbench.bat compare --latest
```

### 第四步：看证据

优先看：

- `cli_transcript.log`
- `cli_diag.json`
- `session_verdict.json`
- `session_brief.md`
- `session_summary.md`
- `compare_brief.md`

## 6. 功能开发场景怎么走

### 第一步：先准备 task

你要有一个 task 文件，例如：

- `agent_workbench/tasks/cli_automation_regression.yaml`

### 第二步：生成实现卡

运行：

```powershell
agent_workbench.bat context --mode feature --stage implement --task agent_workbench\tasks\cli_automation_regression.yaml
```

### 第三步：把最新 `*_paste.md` 粘给 Continue

这一轮只要求 Continue：

- 读阶段卡
- 只改 `allowed_edits`
- 做最小实现
- 不扩 scope

### 第四步：本地回归

运行：

```powershell
agent_workbench.bat build
agent_workbench.bat test generate --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat test run
```

### 第五步：生成验证卡

运行：

```powershell
agent_workbench.bat context --mode feature --stage verify --task agent_workbench\tasks\cli_automation_regression.yaml
```

### 第六步：再把最新 `*_paste.md` 粘给 Continue

这一轮只要求 Continue：

- 执行验证命令
- 读取新 evidence
- 输出结论

### 第七步：跑功能闭环

运行：

```powershell
agent_workbench.bat session feature --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat compare --latest
agent_workbench.bat report --latest
```

## 7. 自动化测试场景怎么走

先运行：

```powershell
agent_workbench.bat context --mode test --stage analyze --task agent_workbench\tasks\cli_automation_regression.yaml
```

然后把最新 `*_paste.md` 粘给 Continue，让它只做测试相关工作。

再运行：

```powershell
agent_workbench.bat test generate --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat test run
```

## 8. 本地模型怎么配合

如果你在迁移后的项目里只能用本地模型，推荐这样做：

1. 在 `agent_workbench.yaml` 里把 `agent.default_profile` 改成 `deepseek16k` 或 `qwen32k`
2. 不要改 `.vscode/tasks.json`
3. 直接继续用 `Context Pack` 任务
4. 一轮只做一个阶段

如果你想了解原因，再看：

- [LOW_CONTEXT_MODELS_GUIDE_ZH.md](LOW_CONTEXT_MODELS_GUIDE_ZH.md)

## 9. 实板问题怎么看

如果 CLI 握手失败，先看：

- `agent_workbench/runtime/cli_diag.json`
- 或 session 目录里的 `cli_diag.json`

优先分类：

- `rx_zero`
- `parser_no_command`
- `tx_or_host_rx`
- `ready_missing`
- `prompt_missing`

先根据分类判断问题位置，再决定是否改代码。

## 10. 给小白的最省事入口

如果你现在就要开始用，最简单的方式是：

1. 直接跑 `Agent Workbench: Direct Verify (CLI Regression)`
2. 打开 [direct_verify_summary.md](/h:/stm32_RAG/code/serial/agent_workbench/runtime/direct_verify_summary.md)
3. 再让 Continue 只基于这份 summary 和链接的 evidence 给结论

如果你不是点 VS Code 任务，而是让 Continue 自己执行命令，推荐它在 PowerShell 里只运行这一条：

```powershell
cmd /c ".\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml"
```

不要让它自己先写 `cd ... && ...`，也不要让它把多条命令串起来。

## 11. 推荐继续看的文件

- [README.md](README.md)
- [LOW_CONTEXT_MODELS_GUIDE_ZH.md](LOW_CONTEXT_MODELS_GUIDE_ZH.md)
- [MIGRATION_GUIDE_ZH.md](MIGRATION_GUIDE_ZH.md)
- [prompts/continue_agent_zh.md](prompts/continue_agent_zh.md)
- [prompts/continue_verify_current_zh.md](prompts/continue_verify_current_zh.md)
- [prompts/continue_low_context_zh.md](prompts/continue_low_context_zh.md)
