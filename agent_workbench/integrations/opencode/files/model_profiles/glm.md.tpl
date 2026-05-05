---
description: GLM-4 系列专用约束，适用于 glm-4 / glm-4-flash / glm-4-plus
---

# GLM 专用补丁

1. 对用户输出使用中文。
2. PowerShell 下优先使用 `.\agent_workbench\bin\agent_workbench.bat <command> --json`。
3. 如果 bat 入口失败，改用 `python ".\agent_workbench\workbench.py" <command> --json`。
4. 一次只运行一条命令，禁止 `;`、`&&` 和管道串联 workbench 命令。
5. 谈到返回值时明确写“返回 JSON 的 `.exit_code == 0`”。
