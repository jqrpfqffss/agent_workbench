# 测试报告模板

## 摘要

- 目标行为：`<测试了什么>`
- 结果：`<pass/fail/blocked>`
- 验证模式：`<UART / diag / monitor / build 自检 / 混合>`
- 板卡/固件：`<board, build artifact, flash result>`

## 覆盖

| 用例 | 目的 | 证据面 | 断言 | 结果 |
|---|---|---|---|---|
| `<case>` | `<为什么重要>` | `<UART/diag/monitor/etc>` | `<expected>` | `<pass/fail/blocked>` |

根据相关性覆盖正常路径、边界、非法输入、状态迁移、reset/restart、时序/趋势和回归场景。

## 证据

- Build：`<build JSON/log path>`
- Flash/reset：`<flash/reset artifact path>`
- UART transcript：`<cli_transcript.log path>`
- Diag result：`<diag artifact path>`
- Monitor samples：`<monitor_samples path>`
- Verify summary：`<direct_verify_summary path>`
- Report/compare：`<report/compare artifact path>`

## 失败分析

- 失败层：`<environment/build/flash/UART/diag/monitor/source behavior/assertion>`
- 支撑分类的证据：`<artifact + field/line>`
- 下一步最小动作：`<probe or fix>`

## 剩余风险

- `<未覆盖边界或硬件条件>`
- `<不稳定证据或环境依赖>`
