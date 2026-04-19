---
description: Qwen-7B 专用约束（适用于 qwen2.5-7b-instruct / qwen3-7b 等小模型）
---

# Qwen-7B 专用补丁

> 适用模型：`qwen2.5-7b-instruct`、`qwen3-7b`。

Qwen-7B 是小模型，上下文受限，针对性约束：

1. **启用 weak_model agent 所有 10 条反例**
2. **每个文件最多读 200 行**：用 `read(path, offset, limit)` 分段
3. **不做代码重构**：只做"添加新功能"，不动现有代码结构
4. **plan.steps 严格按顺序**：禁止跳步，禁止合并步骤
5. **遇到不确定立刻停**：宁可多问用户，不要臆测
