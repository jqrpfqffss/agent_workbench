# 调试方法论

## 分层排查模型

按层定位，不要跳层：

1. 环境层：工具链、路径、配置、串口、烧录器。
2. 构建层：是否构建了预期源码，是否使用正确 artifact。
3. 烧录/复位层：目标是否被正确写入并启动。
4. 启动层：ready banner 是否出现。
5. 传输层：主机 TX、目标 RX、目标 TX、主机 RX 是否连通。
6. CLI/parser 层：命令是否被接收、解析、分派。
7. 功能行为层：命令执行后状态是否正确。
8. 回归层：与上一个通过版本相比哪里变化。

## 假设管理

每次只验证一个假设：

- 假设：`<one sentence>`
- 支持证据：`<artifact/field>`
- 反证：`<artifact/field>`
- 下一条命令：`<single command>`
- 预期结果：`<what would confirm/refute>`

## 高效原则

- 先读 verdict，再读 transcript。
- 先证明确实复现，再改代码。
- 优先选择能区分两个假设的命令。
- 对硬件问题不要无限重试。
- 对 parser/CLI 问题优先使用 `diag exec`。
- 对运行态问题优先使用 `monitor probe`。

## 常见误区

- 看到 no prompt 就改 command handler。
- 看到 assertion fail 就改生产代码。
- 没有 flash 证据却宣称实机验证通过。
- 把 build pass 当作运行正常。
