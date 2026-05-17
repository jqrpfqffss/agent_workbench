# 调试报告模板

最终回复按此结构生成。只引用真实执行过的命令和真实 artifact。

## 摘要

- 结果：`<root cause found / fixed / blocked / inconclusive>`
- 失败层：`<environment/build/flash/reset/UART/diag/monitor/remote-dt/source/regression>`
- 根因：`<one concise statement or unknown>`

## 证据

- `doctor`：`exit_code=<n>`，`<artifact>`
- `build/fix-build`：`exit_code=<n>`，`<build.log or suggested_fixes>`
- `flash/reset`：`exit_code=<n>`，`<flash/reset log>`
- `uart exec`：`exit_code=<n>`，`<cli_transcript.log / uart_exec_result.json>`
- `diag exec`：`exit_code=<n>`，`<diag_exec_result.json / diag_exchange.log>`
- `monitor`：`exit_code=<n>`，`<monitor_samples/stats/log>`
- `remote-dt`：`exit_code=<n>`，`<dt_remote_result/summary/logs>`

## 根因排序

1. `<hypothesis>` - 支持证据：`<artifact/field>`
2. `<hypothesis>` - 支持证据：`<artifact/field>`

## 处理结果

- 修改内容：`<files or none>`
- 修复验证：`<commands and artifacts>`
- 未执行项：`<none / skipped / blocked reason>`

## 剩余风险

- `<risk>`
- 下一条最小动作：`<command or edit>`
