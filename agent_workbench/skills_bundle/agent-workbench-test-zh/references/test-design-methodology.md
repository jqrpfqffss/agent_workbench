# 测试设计方法论

## 先定义行为，不先写断言

每个测试都要回答：

- 用户要证明什么行为？
- 通过什么入口触发？
- 通过什么证据观察？
- 什么结果算通过？
- 哪些旧行为不能被破坏？

## 覆盖层次

- CLI 黑盒：用户可见命令、响应、prompt 恢复。
- 状态查询：status/help/version/diagnostic 等稳定输出。
- diag：请求/响应、timeout、协议错误恢复。
- monitor：变量、计数器、状态机、趋势、范围。
- remote-dt：远端构建、执行、覆盖率或设备流水线。
- 回归：已有命令和稳定字符串不变。
- 负向用例：非法参数、缺参、边界值、错误恢复。

## 好测试的标准

- 一个断言只验证一个行为。
- 字符串短且稳定。
- 不断言时间戳、地址、随机数。
- 至少覆盖正常路径、边界路径、错误路径、回归路径。
- 硬件相关行为必须有 UART/diag/monitor/remote-dt evidence。

## STM32 特别关注

- reset 后 ready/prompt 是否恢复。
- 命令失败后 prompt 是否恢复。
- 中断/主循环状态是否可观察。
- 外设状态是否能通过 status 或 monitor 验证。
- 修改 CLI 时 help 和错误输出是否仍可解析。

## 测试质量门槛

生成测试后必须填或审查覆盖矩阵。见 [test-coverage-matrix.md](test-coverage-matrix.md)。
