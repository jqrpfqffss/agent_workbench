# STM32 Agent Workbench

This workbench is intentionally small. The supported commands are:

- `doctor --json`
- `build --json`
- `fix-build --json`
- `opencode-auto run --task "..." --dry-run --json`
- `opencode-auto run --task-file path --opencode-cmd-template-file path --json`
- `opencode-auto retry --task-file path --opencode-cmd-template-file path --max-attempts 5 --json`
- `opencode-auto retry --task-file path --opencode-cmd-template-file path --no-git-cleanup --json`
- `flash --json`
- `reset --json`
- `uart exec --reset-first --json`
- `uart exec --reset-first --expect-ready --json`
- `diag exec --json`
- `monitor start --json`
- `monitor start --reset-first --json`
- `monitor stop --json`
- `monitor stats --json`
- `remote-dt build --json`
- `remote-dt execute --json`
- `remote-dt coverage --json`
- `remote-dt pipeline --json`
- `remote-dt pull-logs --json`

Run commands from the repository root:

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

If the batch launcher fails, use the direct Python entry:

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

Run a large OpenCode task through the artifact-based orchestrator:

```powershell
python ".\agent_workbench\workbench.py" opencode-auto run --task-file ".\big-task.md" --opencode-cmd-template-file ".\opencode-worker-template.txt" --json
```

Each subtask gets its own attempt directory under `agent_workbench/runtime/opencode_auto/`.

Run the same large task repeatedly until OpenCode succeeds:

```powershell
python ".\agent_workbench\workbench.py" opencode-auto retry --task-file ".\big-task.md" --opencode-cmd-template-file ".\opencode-worker-template.txt" --max-attempts 5 --json
```

`opencode-auto retry` stores compact parent-process output plus detailed artifacts under
`agent_workbench/runtime/opencode_retry/`. Each attempt writes `result.json`, `result.md`,
`stdout.log`, and `stderr.log`; the run root writes `summary.json` and `summary.md`.
By default it requires a clean git worktree so failed attempts can be discarded safely before
the next attempt while preserving retry artifacts. Pass `--no-git-cleanup` to skip the
git safety check and cleanup when the worktree is already dirty or when git is unavailable.

For local OpenCode 1.15.x, a worker template file can contain:

```text
opencode run "Read the attached task file and implement it." -f "{task_file}"
```

Use template files for commands with quoted messages or paths; this avoids Windows shell quoting issues when moving the workbench between projects.
