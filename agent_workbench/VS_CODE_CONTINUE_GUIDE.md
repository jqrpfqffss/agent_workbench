# VS Code + Continue Agent Workflow

This guide explains the fastest reliable path for using VS Code, Continue `Agent` mode, and `agent_workbench`.

## 1. Core Idea

Do not start by feeding a large stack of config, prompts, task yaml, and evidence files into the model.

Use the staged workflow instead:

1. Run a `context` command or the matching VS Code task.
2. Open the newest `*_paste.md` under `agent_workbench/runtime/`.
3. Paste only that file into Continue Agent.
4. Keep one round limited to one stage.

## 2. One-Time Setup

```powershell
setup_workbench.bat
agent_workbench.bat doctor
agent_workbench.bat init-vscode
agent_workbench.bat build
```

## 3. Recommended VS Code Tasks

Open `Terminal: Run Task` and use:

- `Agent Workbench: Doctor`
- `Agent Workbench: Build`
- `Agent Workbench: Context Pack (Debug Analyze)`
- `Agent Workbench: Context Pack (Feature Implement)`
- `Agent Workbench: Context Pack (Feature Verify)`
- `Agent Workbench: Context Pack (Test Analyze)`
- `Agent Workbench: Resume Latest Local-Model Task`
- `Agent Workbench: Debug Session`
- `Agent Workbench: Feature Session (CLI Regression)`
- `Agent Workbench: Compare Latest`
- `Agent Workbench: Report Latest Verdict`

These context tasks now follow `agent.default_profile` from [agent_workbench.yaml](agent_workbench.yaml).

## 4. Debug Flow

```powershell
agent_workbench.bat context --mode debug --stage analyze
```

Paste the newest `*_paste.md` into Continue Agent.

Then, when ready to validate:

```powershell
agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status
agent_workbench.bat session debug
agent_workbench.bat compare --latest
agent_workbench.bat report --latest
```

## 5. Feature Flow

```powershell
agent_workbench.bat context --mode feature --stage implement --task agent_workbench\tasks\cli_automation_regression.yaml
```

Paste the newest `*_paste.md` into Continue Agent and let it implement only the smallest safe change.

Then validate:

```powershell
agent_workbench.bat build
agent_workbench.bat test generate --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat test run
agent_workbench.bat context --mode feature --stage verify --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat session feature --task agent_workbench\tasks\cli_automation_regression.yaml
agent_workbench.bat compare --latest
agent_workbench.bat report --latest
```

## 6. Evidence To Read First

When you need to inspect results manually, start here:

- `session_verdict.json`
- `session_brief.md`
- `session_summary.md`
- `cli_diag.json`
- `cli_transcript.log`
- `assertions.jsonl`
- `compare_brief.md`
- `compare_vs_*.md`

## 7. Local-Model Tip

For DeepSeek / Qwen style local models:

- set `agent.default_profile` in [agent_workbench.yaml](agent_workbench.yaml)
- keep one round to one stage
- use `context --stage resume` when the chat gets full

Read [LOW_CONTEXT_MODELS_GUIDE_ZH.md](LOW_CONTEXT_MODELS_GUIDE_ZH.md) for the full low-context workflow.
