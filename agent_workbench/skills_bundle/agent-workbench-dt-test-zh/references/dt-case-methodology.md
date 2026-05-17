# DT 用例设计方法论

## 先写行为契约

每个 DT 用例先回答：

- 要证明哪个 STM32 行为、host-side 行为或回归风险？
- 远端哪个脚本或测试 runner 触发它？
- 证据来自哪个 remote-dt 阶段：build、execute、coverage、pipeline 或 pull-logs？
- 通过条件落在哪个 artifact：`dt_remote_result.json`、`dt_remote_summary.md`、`logs/dt_*.log`、`results/dt_*_result.json`、`coverage/`？
- 什么结果算通过，什么结果算失败，什么情况算 blocked？

## 覆盖矩阵

优先覆盖：

- 正常路径：有效输入、预期状态变化、稳定结构化 verdict。
- 边界路径：最小/最大值、空输入、重复触发、快速连续触发。
- 错误路径：非法参数、缺参、协议错误、超时恢复。
- 状态路径：远端测试 runner 的初始化状态、错误后恢复、多次运行幂等。
- 回归路径：既有远端用例、既有结果格式、关键日志摘要、关键覆盖率门槛。
- 覆盖率路径：新增逻辑分支、错误处理分支、状态机转移分支。

## STM32 DT 特别规则

- DT skill 不直接调用本地硬件命令；所有硬件或仿真证据都必须由远端脚本执行并通过 remote-dt artifact 拉回。
- 对 LED、GPIO、TIM、ADC 等外设，不凭名称推断参数；必须来自当前源码、生成头文件、远端测试 harness 或 remote-dt evidence。
- 如果远端脚本没有覆盖真实板卡行为，只能报告远端测试通过，不能扩大结论。
- 若本地修改后远端同步状态不可确认，验证结论必须写 blocked 或注明不能证明本地最新改动。

## 断言质量

好的断言：

- 一个断言只验证一个行为。
- 使用结构化字段、短稳定日志标记或覆盖率门槛。
- 能在失败时指向一个 remote-dt 阶段：build、execute、coverage、pull-logs 或远端同步阻塞。

避免：

- 断言长段说明文本。
- 断言时间戳、随机数、绝对地址、日志行号。
- 用示例命令、示例 hex 或示例输出代替当前项目事实。
- 把“文件存在”当作“功能通过”；文件存在只能证明 artifact 拉回成功。
