```text
你现在在一个使用 agent_workbench 的 STM32 项目里工作。

必须遵守：
1. 所有自动化动作优先通过 agent_workbench.bat。
2. PowerShell 下只能使用：
   cmd /c ".\agent_workbench.bat ..."
3. 不要自己写 cd ... && ...、裸 .bat 命令、长命令串。
4. 先看 evidence，再分析，再决定是否改代码。
5. 能用 verify current 时，优先用 verify current。
6. 结论必须基于 direct_verify_summary、session_verdict、session_brief、cli_transcript、cli_diag、assertions。

默认输出结构：
- result: ...
- evidence: ...
- layer: ...
- next: ...
```
