# Evidence-first 根因排序

## 排序原则

根因排序必须基于证据，而不是“看起来像”。

优先级：

1. verdict 明确指出的失败层。
2. diag 分类码。
3. transcript 中的实际收发行为。
4. monitor 运行态数据。
5. compare 差异。
6. 源码阅读。

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
