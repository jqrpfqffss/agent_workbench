# 调试方法论

## 分层排查模型

按层定位，不要跳层：

1. 环境层：工具链、路径、配置、串口、烧录器、remote_dt。
2. 构建层：是否构建了预期源码，是否使用正确 artifact。
3. 烧录/复位层：目标是否被正确写入并启动。
4. 启动层：ready banner 是否出现。
5. 传输层：主机 TX、目标 RX、目标 TX、主机 RX 是否连通。
6. CLI/parser 层：命令是否被接收、解析、分派，prompt 是否恢复。
7. diag 层：请求格式、响应分帧、timeout 是否符合当前项目协议。
8. monitor/debug 层：OpenOCD、符号、地址、value_type 和采样链路是否可靠。
9. 功能行为层：命令执行后状态是否正确。
10. 回归层：与当前任务前的行为或历史 evidence 相比哪里变化。

## 假设管理

每次只验证一个假设：

```text
假设: <one sentence>
支持证据: <artifact/field>
反证: <artifact/field>
下一条命令: <single workbench command>
预期结果: <what would confirm/refute>
```

## 高效原则

- 先证明问题确实复现，再改代码。
- 优先选择能区分两个假设的命令。
- 对硬件问题不要无限重试。
- 对 CLI 问题优先看 `cli_transcript.log` 和 UART result。
- 对运行态问题优先用 monitor 采样闭环。
- 对远端流水线问题优先读 `dt_remote_result.json` 和阶段日志。

## 常见误区

- 看到 no prompt 就改 command handler。
- 看到 assertion fail 就改生产代码。
- 没有 flash 或 UART/diag/monitor 证据却宣称实机验证通过。
- 把 build pass 当作运行正常。
