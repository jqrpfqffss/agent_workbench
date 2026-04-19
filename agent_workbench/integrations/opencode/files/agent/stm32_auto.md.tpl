---
description: STM32 主 agent，负责端到端需求落地
---

# STM32 主 Agent

这是默认的主 agent。行为定义全部在 `AGENTS.md` 里，本文件只做激活标记。

如果 OpenCode 需要在一个会话里显式切换到本 agent，用户输入：

```
@stm32_auto 给 PA8 加 1kHz PWM
```

即进入本 agent 上下文。
