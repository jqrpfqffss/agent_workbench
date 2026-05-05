# 调试报告模板

最终调试回复按此结构生成。

## 调试结论

- 结论：已定位 / 部分定位 / 被阻塞
- 失败层：环境 / 构建 / 烧录 / 启动 / UART / parser / 功能行为 / 测试资产 / 未知
- 最可能根因：`<hypothesis>`

## 现象

- 用户描述：`<symptom>`
- 复现命令：`<command>`
- 是否稳定复现：是 / 否 / 未确认

## 证据链

- `doctor`：`<result + artifact>`
- `build`：`<result + artifact>`
- `uart/diag`：`<classification + artifact>`
- `monitor`：`<key samples or not run>`
- `verify/report`：`<verdict + artifact>`
- `compare`：`<delta or not run>`

## 假设与排除

- 支持的假设：`<hypothesis + evidence>`
- 已排除的假设：`<hypothesis + counter evidence>`
- 证据不足的假设：`<hypothesis + missing evidence>`

## 已采取动作

- `<action and result>`

## 当前阻塞或风险

- `<hardware/environment/permission/risk>`

## 下一条最小实验

- 命令：`<single command>`
- 目的：`<what it will prove>`
