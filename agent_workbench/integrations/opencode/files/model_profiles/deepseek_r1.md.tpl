---
description: DeepSeek-R1 专用约束（适用于 deepseek-r1 / deepseek-reasoner）
---

# DeepSeek-R1 专用补丁

> 适用模型：`deepseek-r1`、`deepseek-reasoner`。

DeepSeek-R1 是推理模型，特点是慢但精确。针对性约束：

1. **一次一步**：不要一轮给多个步骤的推理，每完成一个 workbench 命令就停下来等结果
2. **不要贴大段思考**：推理过程保留在内部，输出只要结论 + 下一步命令
3. **JSON 解析优先级最高**：所有判断基于 workbench 命令返回的 JSON，不基于文本推理
4. **Period 长度限制**：一次最多执行 3 步 plan.steps，然后汇报给用户
