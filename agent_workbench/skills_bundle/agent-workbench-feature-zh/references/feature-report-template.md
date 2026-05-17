# 功能开发报告模板

最终回复按此结构生成。只引用真实执行过的命令和真实 artifact。

## 功能结果

- 结论：完成 / 部分完成 / 阻塞
- 目标：`<goal>`

## 修改内容

- 修改文件：`<file list>`
- 使用的 runtime probe / CLI 命令 / 可观测路径：`<items>`
- 保持稳定的字符串：`<ready/prompt/help/status/ack>`

## 验证证据

- `doctor`：`exit_code=<n>`，关键证据 `<artifact>`
- `build`：`exit_code=<n>`，关键证据 `<artifact>`
- `flash/reset`：`exit_code=<n>`，证据 `<artifact>`，如已执行
- `uart exec`：`exit_code=<n>`，证据 `<cli_transcript.log / uart_exec_result.json>`，如已执行
- `diag exec`：`exit_code=<n>`，证据 `<diag result/log>`，如已执行
- `monitor`：`exit_code=<n>`，证据 `<monitor samples/stats/log>`，如已执行
- `remote-dt`：`exit_code=<n>`，证据 `<dt result/summary/logs>`，如已执行

## 行为验证

- 已验证的新行为：`<behavior>`
- 使用命令：`<cli/diag/monitor/remote-dt command>`
- 关键 transcript / monitor / remote evidence：`<short evidence>`

## 风险与限制

- 未执行的实机动作：`<none / skipped / blocked>`
- 未覆盖的边界：`<items>`
- 需要用户处理的阻塞：`<items>`

## 下一步

- 推荐下一步：`<one concise next step>`
