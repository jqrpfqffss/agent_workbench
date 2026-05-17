# 断言模式

## CLI 断言

优先：

- ready banner 出现
- prompt 出现或命令后恢复
- transcript 包含短稳定响应
- transcript 不包含明确错误字符串
- 命令没有 timeout

字符串来源：

- `doctor` 或配置中的 ready/prompt。
- 当前 CLI transcript。
- 用户需求或明确行为契约定义的新 ack/status 字符串。

## Monitor 断言

运行态重要时使用：

- 最后值在范围内
- 采样中出现某状态
- 计数器单调增加
- 趋势方向符合预期
- item 没有 read error

不要用瞬时精确值断言抖动变量。

## Diag 字段断言

当 `diag_exec_result.json` 有稳定字段时使用：

- exchange count
- timeout count
- request/response bytes
- 分类或错误码

字段不存在时不要强行断言。

## Remote DT 断言

- 阶段 exit_code 为 0。
- 远端 result JSON verdict/pass 字段符合约定。
- 覆盖率 artifact 存在并达到用户定义门槛。
- 阶段日志没有明确 fatal/error。

## 文件断言

需要确认产物存在时使用文件存在性和路径报告，但文件存在不等同于功能通过。

## 坏模式

- 断言长段自然语言。
- 断言时间戳、地址、随机 ID。
- 断言示例字符串而非当前项目字符串。
- 一个断言同时验证多个行为。
