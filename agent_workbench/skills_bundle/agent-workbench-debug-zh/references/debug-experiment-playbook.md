# 调试实验 Playbook

## 实验模板

```text
实验目标: <要区分的假设>
命令: <单条 workbench 命令>
观察字段: <JSON 字段或 artifact>
通过说明: <看到什么意味着假设成立>
失败说明: <看到什么意味着假设被否定>
下一步: <根据结果走哪条路由>
```

## 环境实验

- 目标：确认工具链、配置、串口、烧录器可用。
- 命令：`doctor --json`
- 失败：停止，不改源码。

## 构建实验

- 目标：确认当前源码能生成固件。
- 命令：`build --json`
- 失败：`fix-build --json`。

## 烧录实验

- 目标：确认固件进入目标板。
- 命令：`flash --json`
- 注意：不需要用户授权；任务需要时直接执行。

## UART 握手实验

- 目标：确认 ready/prompt。
- 命令：`uart exec --reset-first --expect-ready --command <probe> --json`
- 失败：读 `cli_diag.json` 和 transcript。

## Parser 实验

- 目标：确认命令是否到达并被解析。
- 命令：`diag exec ... --json`
- 结果：
  - `parser_no_command` 指向命令表/输入处理。
  - `rx_zero` 指向链路/启动。

## 运行态实验

- 目标：确认变量、状态机或外设状态。
- 命令：`monitor probe --json`
- 失败：确认符号、目标运行、probe 配置。

## 回归实验

- 目标：判断新失败是否由最近改动引入。
- 命令：`compare --latest --json`
- 关注：新增失败、已解决失败、transcript/monitor 差异。
