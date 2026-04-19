# agent_workbench 集成包架构迁移指南

这次迁移的目标不是“只切到某一个 AI 前端”，而是把 `agent_workbench` 核心能力和 AI 前端配置彻底解耦：

- `agent_workbench/core/` 继续负责 doctor、build、flash、uart、plan、verify、report
- `agent_workbench/integrations/<name>/` 负责生成具体前端所需文件
- 统一入口改为 `agent_workbench.bat integration ...`

## 场景 A：从旧的 Continue-only 版本迁移

建议步骤：

1. 同步到包含新架构的代码版本。
2. 运行环境检查：

```powershell
cmd /c ".\agent_workbench.bat doctor --json"
```

3. 安装你需要的 integration：

```powershell
cmd /c ".\agent_workbench.bat integration install continue --json"
cmd /c ".\agent_workbench.bat integration install opencode --json"
```

4. 用下面命令确认结果：

```powershell
cmd /c ".\agent_workbench.bat integration list --json"
cmd /c ".\agent_workbench.bat integration check continue --json"
cmd /c ".\agent_workbench.bat integration check opencode --json"
```

## 场景 B：从“硬切换到 OpenCode”的过渡版本迁移

这个场景最常见的特征是：

- 根目录仍然只有 OpenCode 文档
- `init-opencode-agents` 仍被当作主入口
- 还没有 `continue` integration 包

迁移后：

- `init-opencode-agents` 只是兼容 shim
- 正式入口是 `integration install opencode`
- Continue 规则重新通过 `integration install continue` 生成

推荐命令：

```powershell
cmd /c ".\agent_workbench.bat integration install opencode --json"
cmd /c ".\agent_workbench.bat init-opencode-agents --json"
```

上面两条命令应生成等价的 OpenCode 文件集。

## 场景 C：新项目空仓初始化

1. 先完成环境准备：

```powershell
agent_workbench\bin\setup.bat
cmd /c ".\agent_workbench.bat doctor --json"
cmd /c ".\agent_workbench.bat init-vscode --json"
```

2. 按团队需要安装 integration：

```powershell
cmd /c ".\agent_workbench.bat integration install opencode --json"
cmd /c ".\agent_workbench.bat integration install continue --json"
```

3. 再开始 plan / verify / context 工作流。

## 迁移后你会看到什么

- `AGENTS.md`、`opencode.json`、`.opencode/` 由 `opencode` integration 生成
- `.continue/rules/` 由 `continue` integration 生成
- `README.md` 与各 integration 的 `README_ZH.md` 分别承担核心说明和前端说明

## 建议的检查清单

```powershell
cmd /c ".\agent_workbench.bat doctor --json"
cmd /c ".\agent_workbench.bat integration list --json"
cmd /c ".\agent_workbench.bat test run --json"
```

如果你需要追溯旧方案文档，可以去 `docs/history/` 查看历史资料。
