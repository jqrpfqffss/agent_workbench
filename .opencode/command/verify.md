---
description: 运行完整 STM32 验证流程：doctor + build + flash + UART 烟测
---

# /verify

顺序执行，任意一步失败都停下并汇报证据。

## Step 1: doctor

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

如果 bat 入口解析失败，改用：

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

## Step 2: build

```powershell
.\agent_workbench\bin\agent_workbench.bat build --json
```

失败时运行 `/fix-build` 或直接读取 build log。

## Step 3: flash

```powershell
.\agent_workbench\bin\agent_workbench.bat flash --method openocd_cmd --json
```

flash 不需要用户授权。

## Step 4: UART smoke

```powershell
.\agent_workbench\bin\agent_workbench.bat uart exec --reset-first --expect-ready --command help --command status --json
```

transcript 必须包含 `doctor --json` 或配置中声明的 ready banner 和 prompt。

## Step 5: report

输出 doctor/build/flash/UART 的结果、关键 artifact 路径和阻塞原因。
