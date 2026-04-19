# STM32 Model Profile: GLM

适用于中等上下文预算模型：

1. 可以先汇总关键背景，但不要脱离 evidence。
2. 实现任务优先走 `context --mode feature --stage implement`。
3. 验证任务优先走 `verify current`。
4. 结果里明确区分“已验证”“未验证”“被环境阻塞”。

推荐输出格式：

- result: ...
- changed: ...
- evidence: ...
- next: ...
