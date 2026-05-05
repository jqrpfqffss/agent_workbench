# 断言模式

## CLI 断言

优先：

- `cli_contains`
- `cli_not_contains`
- `cli_ready`
- `cli_prompt_seen`
- `cli_no_timeout`

字符串来源：

- `doctor` 或配置中的 ready/prompt。
- 当前 CLI transcript。
- 用户需求或明确行为契约定义的新 ack/status 字符串。

## Monitor 断言

运行态重要时使用：

- `monitor_last_between`
- 范围断言
- 趋势断言

不要用瞬时精确值断言抖动变量。

## 文件断言

需要确认产物存在时使用 `file_exists`。

## diag 字段断言

当 `cli_diag.json` 有稳定数字字段时使用：

- 命令计数
- timeout 计数
- rx byte 计数
- parser error 计数

字段不存在时不要强行断言。

## 坏模式

- 断言长段自然语言。
- 断言时间戳、地址、随机 ID。
- 断言示例字符串而非当前项目字符串。
- 一个断言同时验证多个行为。
