# 测试报告模板

## 摘要

- 目标行为：`<测试了什么>`
- 结果：`<pass/fail/blocked>`
- 验证模式：`<UART / diag / monitor / remote-dt / build / 混合>`
- 板卡/固件：`<board, build artifact, flash result>`

## 覆盖

| 用例 | 目的 | 证据面 | 断言 | 结果 |
|---|---|---|---|---|
| `<case>` | `<为什么重要>` | `<UART/diag/monitor/remote-dt/etc>` | `<expected>` | `<pass/fail/blocked>` |

根据相关性覆盖正常路径、边界、非法输入、状态迁移、reset/restart、时序/趋势和回归场景。

## 证据

- Doctor：`<exit_code and doctor_report path>`
- Build：`<exit_code and build log path>`
- Flash/reset：`<exit_code and artifact path>`
- UART transcript：`<exit_code and cli_transcript.log path>`
- Diag result：`<exit_code and diag artifact path>`
- Monitor samples/stats：`<exit_code and monitor artifact path>`
- Remote DT：`<exit_code and dt result/summary/logs>`

## 失败分析

- 失败层：`<environment/build/flash/UART/diag/monitor/remote-dt/source behavior/assertion>`
- 支撑分类的证据：`<artifact + field/line>`
- 下一步最小动作：`<probe or fix>`

## 剩余风险

- `<未覆盖边界或硬件条件>`
- `<不稳定证据或环境依赖>`
