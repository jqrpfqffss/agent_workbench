# agent-workbench-test

## 适用场景

当用户需要：

- 自动生成测试资产
- 执行测试
- 分析测试失败
- 判断失败是在 task、测试资产，还是源码行为

时使用本技能。

## 目标

让模型先把“测试体系本身”跑清楚，而不是一失败就把锅甩给源码。

## 默认流程

先确认 task 文件，然后运行：

```powershell
cmd /c ".\agent_workbench.bat test generate --task <任务文件.yaml>"
cmd /c ".\agent_workbench.bat test run"
```

如果当前模型上下文紧张，或者任务很复杂，可以先生成阶段卡：

```powershell
cmd /c ".\agent_workbench.bat context --mode test --stage analyze --task <任务文件.yaml>"
```

然后只读最新 `*_paste.md`。

## 必读文件

优先读取：

- `agent_workbench/runtime/unit.log`
- `agent_workbench/generated/tasks/<task_id>/blackbox_assertions.yaml`
- `agent_workbench/generated/tasks/<task_id>/unit_test_plan.md`
- `agent_workbench/generated/tasks/<task_id>/implementation_brief.md`
- `agent_workbench/generated/tasks/<task_id>/task_snapshot.json`

## 判断顺序

### 第一层：task 定义是否合理

如果 task 本身验收项写错了，先报告 task 问题。

### 第二层：生成的测试资产是否合理

如果 task 没问题，但生成的 assertions / plan 太弱或不稳定，先报告测试资产问题。

### 第三层：源码行为是否真的违反验收

只有前两层都合理，才把问题归因到源码行为。

## 行为约束

1. 测试请求优先处理测试，不要一上来大改业务代码
2. 输出匹配尽量稳定、机器可断言
3. 先指出第一失败层，不要把一堆失败混在一起讲
4. 如果用户没有明确要求修复，不要默认进入功能实现

## 输出要求

按这个顺序输出：

1. `测试结果`
2. `使用的测试资产`
3. `第一失败层`
4. `建议下一步`

如需固定模板，使用：

- `templates/test-report-template.md`

如需详细判断规则，读取：

- `references/test-judgement.md`
