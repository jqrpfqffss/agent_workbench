# 测试判断规则

## 一、先区分是哪一层失败

### 1. task 层

表现：

- 验收项与当前功能目标不一致
- 断言目标写错
- scope 太宽或太窄

动作：

- 先建议修 task yaml

### 2. 测试资产层

表现：

- `blackbox_assertions.yaml` 不稳定
- `unit_test_plan.md` 覆盖不对
- 生成的命令、输出断言与实际需求不匹配

动作：

- 先建议修测试资产或重新生成

### 3. 源码行为层

表现：

- task 与测试资产都正确
- 运行结果仍明确违反验收

动作：

- 这时再转入功能修复或功能验证

## 二、优先使用的证据

1. `unit.log`
2. `task_snapshot.json`
3. `blackbox_assertions.yaml`
4. `unit_test_plan.md`
5. `implementation_brief.md`

## 三、常见错误

1. 测试一失败就立刻改源码
2. 不检查 task 是否仍然是旧规格
3. 不检查生成资产是否已经过期
