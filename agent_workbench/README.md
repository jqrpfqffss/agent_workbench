# STM32 Agent Workbench

This workbench is intentionally small. The supported commands are:

- `doctor --json`
- `build --json`
- `fix-build --json`
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
- `remote-dt push-files --json`
- `opencode-auto run --task "..." --json`

Run commands from the repository root:

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

If the batch launcher fails, use the direct Python entry:

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

## remote-dt push-files

Push local project files (DT scripts, source code, test fixtures) to the remote Linux
server using SCP. All settings come from `agent_workbench.yaml` under
`remote_dt.push_files`; there are no CLI flags for `--local-dir` or `--remote-dir`.

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt push-files --json
```

With an explicit config path:

```powershell
.\agent_workbench\bin\agent_workbench.bat remote-dt push-files --config ".\agent_workbench\agent_workbench.yaml" --json
```

### Configuration (agent_workbench.yaml)

```yaml
remote_dt:
  push_files:
    enabled: true
    local_dir: ".\\agent_workbench\\runtime\\dt_upload"
    remote_dir: "/home/dtuser/project/upload"
    timeout_sec: 600
    dry_run: false
    exclude:
      - "**/__pycache__/**"
      - "**/*.pyc"
      - "**/.pytest_cache/**"
      - "**/.git/**"
    normalize_lf_for_shell_scripts: true
    chmod_executable_for_shell_scripts: true
    verify_shell_scripts_after_upload: true
```

### Behavior

1. Enumerate all files under `local_dir`, apply `exclude` glob patterns.
2. Stage files in a local staging directory under `local_artifact_dir/push_staging`.
3. Detect shell scripts (by suffix `.sh`/`.bash`/`.zsh`/`.ksh`, by well-known names
   like `build`/`build.sh`/`execute`/`coverage`, or by shebang in the first 512 bytes).
4. Convert CRLF to LF in staged shell scripts when `normalize_lf_for_shell_scripts`
   is true. Source files under `local_dir` are never modified.
5. Upload staging contents to `remote_dir` via `scp -r <staging>/. user@host:<remote_dir>`.
6. Optionally `chmod +x` all detected shell scripts on the remote side.
7. Optionally verify remote shell scripts, including `build.sh` (check for CRLF residue, run `bash -n`).

Use `dry_run: true` to validate local config and file counts without any SSH/SCP calls.
