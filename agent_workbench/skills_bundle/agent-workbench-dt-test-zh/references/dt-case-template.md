# DT 用例模板

## 用例矩阵

没有项目既有格式时，可在报告或测试规格中使用这个最小矩阵：

| id | 行为契约 | 触发 | 观测面 | 期望 | 失败归因线索 |
|---|---|---|---|---|---|
| `DT-001` | `<要证明的行为>` | `<远端脚本/测试 runner/输入>` | `<remote-dt 阶段和 artifact>` | `<短稳定断言>` | `<先看哪个日志或字段>` |

## 推荐 case 元数据

若项目没有测试框架约定，可以让 DT 用例或测试报告输出结构化 JSON，便于 remote-dt 归档：

```json
{
  "suite": "stm32-dt",
  "case_id": "DT-001",
  "name": "short behavior name",
  "target": "module-or-feature",
  "trigger": "how the behavior is exercised",
  "expected": "stable pass condition",
  "observed": "actual concise observation",
  "verdict": "pass",
  "evidence": [
    "agent_workbench/runtime/remote_dt/logs/dt_execute.log"
  ]
}
```

`verdict` 只使用 `pass`、`fail`、`blocked`。`blocked` 必须写明阻塞条件，例如 remote_dt 未启用、远端代码未同步、SSH 不通、远端测试环境不可用或缺少协议说明。

## 结果汇总建议

远端 `execute.sh` 若能控制输出，建议最终生成或打印类似摘要：

```text
DT_RESULT suite=stm32-dt total=3 pass=3 fail=0 blocked=0
DT_CASE id=DT-001 verdict=pass evidence=dt_execute.log
```

这样 `remote-dt` 的日志解析和人工阅读都更稳定。不要依赖彩色终端、交互输入或只在人眼可读的表格中表达唯一结果。

## 文件落地规则

- 优先使用项目已有测试目录和命名风格。
- 如果没有约定，创建最小新增目录，例如 `tests/dt/` 或项目已有测试根目录下的 `dt/`。
- 不新增大型框架，除非当前项目已经使用该框架或用户明确要求。
- 若修改 `execute.sh`，保持非交互式、可重复运行、失败返回非 0。
- 若新增覆盖率门槛，把门槛写成清晰变量或配置，不埋在长命令里。
