Use this template when context is tight or the local model starts to drift.

Global rules:

1. Do one stage per chat round.
2. Always use `cmd /c ".\agent_workbench.bat ..."` for automation.
3. Read only the newest `*_paste.md` generated under `agent_workbench/runtime/`.
4. Do not reopen README or large guides unless the stage card explicitly requires it.
5. Do not claim anything without evidence files or fact IDs.

Analyze round:

```powershell
cmd /c ".\agent_workbench.bat context --mode <debug|feature|test> --stage analyze --task <task.yaml>"
```

Then read only the newest `*_paste.md`.
In this round:

- analyze symptoms
- rank root causes
- propose one next action
- do not edit code

Implement round:

```powershell
cmd /c ".\agent_workbench.bat context --mode feature --stage implement --task <task.yaml>"
```

Then read only the newest `*_paste.md`.
In this round:

- read only `allowed_reads`
- edit only `allowed_edits`
- keep the change minimal
- do not widen scope

Verify round:

```powershell
cmd /c ".\agent_workbench.bat context --mode feature --stage verify --task <task.yaml>"
```

Then read only the newest `*_paste.md`.
In this round:

- run only workbench commands
- read only the newest evidence
- conclude from evidence only

Resume round:

```powershell
cmd /c ".\agent_workbench.bat context --stage resume"
```

Then read only the newest `*_resume.md` and `*_paste.md`.
In this round:

- continue the same stage
- do not reload the whole project
- do not restart from scratch
