# 低上下文本地模型使用指南

这份指南专门给 DeepSeek-R1 / Qwen 这类小上下文、高幻觉、本地部署模型使用。

## 1. 先理解新的工作方式

现在不要再把一大堆文件一次性喂给模型。

正确做法是：

1. 先让 `agent_workbench` 生成当前阶段的上下文卡。
2. 再把最新生成的 `*_paste.md` 粘给 Continue Agent。
3. 一轮只做一个阶段。
4. 上下文快满时，不回顾整段历史，直接跑 `context --stage resume`。

这样做的目的有两个：

- 把输入压到 profile 预算内
- 把“容易乱猜”的空间压到最小

## 2. 先选 profile

本地模型 profile 在 [agent_workbench.yaml](agent_workbench.yaml) 的 `agent.profiles` 里定义。

默认可用 3 个：

- `balanced_local`
- `deepseek16k`
- `qwen32k`

推荐做法：

- DeepSeek-R1 小上下文场景：把 `agent.default_profile` 设为 `deepseek16k`
- Qwen 32K 场景：把 `agent.default_profile` 设为 `qwen32k`
- 如果你不确定：先用 `balanced_local`

VS Code 任务现在默认跟随 `agent.default_profile`，所以迁移到别的项目后通常只需要改配置，不需要改 `.vscode/tasks.json`。

## 3. 每个阶段会生成什么

运行 `agent_workbench.bat context ...` 后，会在 `agent_workbench/runtime/` 生成：

- `*_brief.md`
  一屏摘要，给人快速读
- `*_facts.json`
  只保留可引用事实，带 `fact_id`
- `*_constraints.json`
  本轮允许读取哪些文件、允许改哪些文件、禁止猜什么
- `*_resume.md`
  上下文满了以后下一轮直接续接
- `*_paste.md`
  直接粘给 Continue Agent 的最短提示
- `agent_state.json`
  当前模式、阶段、profile、最近 session、下一步命令

## 4. 标准使用顺序

### 4.1 一次性准备

```powershell
setup_workbench.bat
agent_workbench.bat doctor
agent_workbench.bat init-vscode
agent_workbench.bat build
```

### 4.2 调试任务

```powershell
agent_workbench.bat context --mode debug --stage analyze
```

然后：

1. 打开 `agent_workbench/runtime/` 里最新的 `*_paste.md`
2. 粘给 Continue Agent
3. 让它只分析，不改代码
4. 分析结束后再决定是否进入实现或验证

### 4.3 功能实现任务

```powershell
agent_workbench.bat context --mode feature --stage implement --task agent_workbench\tasks\<TASK>.yaml
```

然后：

1. 打开最新 `*_paste.md`
2. 粘给 Continue Agent
3. 让它只做最小修改
4. 修改后再进入验证阶段

### 4.4 验证任务

```powershell
agent_workbench.bat context --mode feature --stage verify --task agent_workbench\tasks\<TASK>.yaml
```

然后：

1. 打开最新 `*_paste.md`
2. 粘给 Continue Agent
3. 让它只执行 workbench 命令并基于新 evidence 下结论

### 4.5 上下文满了怎么办

```powershell
agent_workbench.bat context --stage resume
```

然后把最新 `*_paste.md` 继续粘给 Continue。

不要把旧对话一大段回贴给模型，也不要重新让它从 README 开始读。

## 5. 一轮里绝对不要做的事

- 不要同时让模型分析、改代码、跑验证
- 不要让模型自己通读整个仓库
- 不要让模型凭源码印象替代 evidence
- 不要让模型自己拼一堆散命令绕开 `agent_workbench.bat`
- 不要在没有新 evidence 的情况下宣称“已修复”

## 6. 推荐的最短操作法

这是最适合 16K/32K 本地模型的方式：

1. 在 VS Code 运行对应的 `Context Pack` 任务
2. 打开 `agent_workbench/runtime/` 下最新 `*_paste.md`
3. 整段复制到 Continue Agent
4. 等它做完当前阶段
5. 再切下一阶段

## 7. 为什么这比长提示词更稳

因为新流程把下面这些东西从“模型记忆”里移到了“workbench 产物”里：

- 当前 task 是什么
- 当前证据里已经确认了什么
- 当前阶段允许读哪些文件
- 当前阶段允许改哪些文件
- 当前下一步只能跑哪些命令

模型每一轮只要处理当前阶段，不需要背整个项目。

## 8. 推荐看的文件

- [README.md](README.md)
- [VS_CODE_CONTINUE_GUIDE_ZH.md](VS_CODE_CONTINUE_GUIDE_ZH.md)
- [MIGRATION_GUIDE_ZH.md](MIGRATION_GUIDE_ZH.md)
- [prompts/continue_low_context_zh.md](prompts/continue_low_context_zh.md)

## 9. 常见问题

### 9.1 为什么 doctor 还会有 warning

最常见的 3 类 warning：

- `pyserial` 没装
  不影响 `uart exec` 和 session 基础流程，PowerShell fallback 还能工作
- 还没生成过 context
  这时 `agent_state.json`、`*_paste.md` 还不存在
- 当前机器上没有实板 / COM 口 / 烧录器
  这属于环境问题，不是 workbench 代码问题

### 9.2 为什么还建议看 evidence

因为高幻觉模型最怕“猜”。`facts.json` 和 `session_verdict.json` 是模型的最小事实源，`cli_transcript.log`、`assertions.jsonl` 是最终证据源。

### 9.3 什么时候需要显式写 `--profile`

只有两种情况：

- 你想临时覆盖 `agent.default_profile`
- 你想比较同一任务在不同 budget 下的卡片长度

平时不写 `--profile` 也可以。
