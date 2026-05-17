# Evidence-first 根因排序

## 排序原则

根因排序必须基于证据，而不是“看起来像”。

优先级：

1. `doctor` 明确指出的环境/配置阻塞。
2. 命令 JSON 的 `exit_code`、`status`、`summary`。
3. UART transcript 和 UART result 中的实际收发行为。
4. diag result/exchange 中的请求、响应、timeout。
5. monitor samples/stats/log 中的运行态数据。
6. remote-dt result/summary/log 中的远端阶段结果。
7. 源码阅读。

## 输出格式

```text
最可能根因:
1. <hypothesis> - 支持证据: <artifact/field>
2. <hypothesis> - 支持证据: <artifact/field>

已排除:
- <hypothesis> - 反证: <artifact/field>

下一条最小实验:
- <command>
```

## 不足证据时

不要给确定结论。写：

- 当前只能定位到哪一层。
- 缺哪份证据。
- 下一条最小命令是什么。
