# 功能闭环说明

## 一、标准闭环

### 验证型闭环

```powershell
cmd /c ".\agent_workbench.bat verify current --task <任务文件.yaml>"
```

适用：

- 当前只想判断是否通过
- 当前不打算改代码

### 实现 + 验证闭环

```powershell
cmd /c ".\agent_workbench.bat context --mode feature --stage implement --task <任务文件.yaml>"
```

按阶段卡实现后，再运行：

```powershell
cmd /c ".\agent_workbench.bat verify current --task <任务文件.yaml>"
```

## 二、什么时候用显式长流程

只有在以下情况才需要：

1. 需要单独看 test generate / test run 的中间产物
2. 需要单独拿到 `session feature` 的证据
3. 需要 `compare --latest` 做回归对比

否则优先 `verify current`。

## 三、功能类任务最容易出错的点

1. 没有先确认 task
2. 读了太多无关源码
3. 明明只要小改，却把 scope 改大
4. 改完代码没有重新做自动化验证
