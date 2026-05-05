# 调试命令 Playbook

## 什么时候用 `uart exec`

- 需要观察 ready/prompt。
- 需要执行一个或多个 CLI 命令。
- 需要黑盒 transcript。

## 什么时候用 `diag exec`

- UART 有异常但需要分类。
- 怀疑 rx/tx/parser/prompt 问题。
- 需要比 transcript 更结构化的诊断字段。

## 什么时候用 `monitor probe`

- 功能状态不一定体现在 CLI 输出。
- 需要变量、计数器、状态机、趋势或范围证据。

## 什么时候用 `report --latest`

- 准备向用户汇报。
- 需要统一 session evidence。

## 什么时候用 `compare --latest`

- 用户说“以前可以现在不行”。
- 需要证明修复前后差异。
- 需要判断新增回归或已解决问题。
