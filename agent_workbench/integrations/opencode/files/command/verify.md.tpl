---
description: 运行完整 STM32 验证流程（doctor + build + flash + uart 烟测）
---

# /verify 命令

顺序执行以下步骤，任意一步失败立即停下并汇报：

## Step 1: doctor
```
cmd /c ".\agent_workbench.bat doctor --json"
```
- `fail_count > 0` → 停下来列出所有 fail 项

## Step 2: build
```
cmd /c ".\agent_workbench.bat build --json"
```
- `exit_code != 0` → 调 `/fix-build`

## Step 3: 征询烧录
询问用户："是否烧录并做 UART 烟测？(yes/no)"

## Step 4: flash（用户同意后）
```
cmd /c ".\agent_workbench.bat flash --method openocd_cmd --json"
```

## Step 5: uart smoke
```
cmd /c ".\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json"
```
- transcript 必须含 `{ready_banner}` 和 `{prompt}`

## Step 6: 报告
输出合并摘要：
```
/verify 完成:
  doctor: ok (N 项检查通过)
  build: ok (elf size=KB)
  flash: ok
  uart: ok (ready banner 第 L 行出现, prompt K 次)
```
