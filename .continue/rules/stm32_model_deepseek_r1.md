# STM32 Model Profile: DeepSeek-R1

适用于推理型模型，要求更强约束：

1. 先执行命令，再解释，不要长篇预案。
2. 结论只保留最关键证据。
3. 若需求不清楚，先做最小验证，不要擅自扩 scope。
4. 如果用户要求改代码，先跑 `plan` 或 `context`，再动手。

推荐输出格式：

- result: ...
- evidence: ...
- layer: ...
- next: ...
