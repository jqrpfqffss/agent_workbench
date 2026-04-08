# 通用输出模板

请按下面结构输出：

## 结果

- 通过 / 未通过 / 环境阻塞

## 证据链

- 引用哪个 summary
- 引用哪个 verdict / transcript / diag / assertions
- 这些证据分别说明了什么

## 失败层级

- doctor / build / test_run / flash-reset / uart_smoke / feature_session

## 下一步

- 只给一个最小下一步
- 如果是环境问题，不要建议改代码
