---
description: GLM-4 系列专用约束
model:
  - glm-4
  - glm-4-flash
  - glm-4-plus
---

# GLM 专用补丁

GLM-4 在中文指令理解上很好，但对 shell 命令语法敏感，针对性约束：

1. **中文输出**：所有对用户的回复用中文
2. **PowerShell 语法**：Windows 下命令必须用 `cmd /c "..."` 包起来
3. **一次一条**：禁止 `;` 和 `&&` 串联
4. **JSON 字段引用**：谈到返回值时明确写 `返回 JSON 的 .exit_code == 0`，不要简称
