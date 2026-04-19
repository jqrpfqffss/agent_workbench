# STM32 Error Recovery

遇到失败时按下面顺序处理：

1. `doctor` 有 fail：先停下，报告 fail 项，不直接继续。
2. `build` 失败：运行 `fix-build`，最多修 3 轮，再汇报阻塞点。
3. `verify current` 失败：先看 `direct_verify_summary.*`，再看 `cli_diag.json` 和 `cli_transcript.log`。
4. `integration check` 不通过：优先重新执行 `integration install <name>`，再复查生成文件。
5. 硬件相关动作失败：不要盲目重试超过 1 次，先把证据返回给用户。

关键命令：

```powershell
cmd /c ".\agent_workbench.bat fix-build --json"
cmd /c ".\agent_workbench.bat report --latest --json"
cmd /c ".\agent_workbench.bat integration check continue --json"
```
