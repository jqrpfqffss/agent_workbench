# Qwen 7B 专用规则

如果你是 Qwen 7B，请额外遵守以下要求：

1. 先读 `plan.constraints.allowed_edit_files`，再决定读写范围。
2. 路径统一使用 `/`，命令统一用 `cmd /c ".\agent_workbench.bat ..."`。
3. 不要把多条 shell 命令拼成一行，也不要用 `cd xxx; command`。
4. 优先读取 `errors[0]`、`diagnosis.summary` 这类高信号字段，不要一次分析整段日志。
5. 需要修改代码时，优先做最小补丁，不要顺手重构无关逻辑。
6. 在 `serial` 项目里，如果 CLI 验证失败，先看 `cli_diag.json`，再看 `cli_transcript.log`。
