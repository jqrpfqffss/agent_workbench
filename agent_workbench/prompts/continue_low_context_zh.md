# Continue 低上下文阶段模板

这份模板面向 DeepSeek-R1 / Qwen 这类小上下文、本地部署、容易幻觉的模型。

默认原则：

1. 配置里先选好 `agent.default_profile`。
2. 每一轮先运行 `agent_workbench.bat context ...`。
3. 只把当前阶段最新生成的 `*_paste.md` 粘给 Continue。
4. 一轮只做一个阶段，不混做分析、实现、验证。
5. 不允许模型自行扩读大文件，只能按 `constraints.json` 行动。

如果你想临时覆盖默认 profile，再额外加 `--profile deepseek16k` 或 `--profile qwen32k`。

## 1. 调试分析阶段

先执行：

```powershell
agent_workbench.bat context --mode debug --stage analyze
```

再把最新 `*_paste.md` 粘给 Continue。

本轮要求：

- 只分析 evidence
- 不改代码
- 不读大文件
- 只给出根因排序和唯一下一步

## 2. 功能实现阶段

先执行：

```powershell
agent_workbench.bat context --mode feature --stage implement --task agent_workbench\tasks\<TASK>.yaml
```

再把最新 `*_paste.md` 粘给 Continue。

本轮要求：

- 只做最小修改
- 只允许读 `constraints.json` 里的 `allowed_reads`
- 只允许改 `allowed_edits`
- 不扩 scope

## 3. 验证阶段

先执行：

```powershell
agent_workbench.bat context --mode feature --stage verify --task agent_workbench\tasks\<TASK>.yaml
```

再把最新 `*_paste.md` 粘给 Continue。

本轮要求：

- 只执行 workbench 命令
- 只读最新 evidence
- 结论必须引用 `session_verdict.json`、`session_brief.md`、`assertions.jsonl`、`cli_transcript.log`

## 4. 续接阶段

如果上下文快满，先执行：

```powershell
agent_workbench.bat context --stage resume
```

再把最新 `*_paste.md` 粘给 Continue。

本轮要求：

- 不重新从 README 开始
- 只基于 `agent_state.json` 和最新 `*_resume.md` 续接
- 继续当前阶段，而不是重新发散

## 5. 可直接粘贴给 Continue 的最短说明

```text
Read only the newest *_paste.md generated under agent_workbench/runtime.
Follow its stage rules exactly.
Use agent_workbench.bat for every automation action.
Do not read extra files unless they are listed in allowed_reads.
Do not claim anything without citing fact_id or evidence files.
```
