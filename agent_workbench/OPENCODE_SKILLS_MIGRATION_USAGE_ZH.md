# OpenCode 四 Skill 迁移使用教程

本文说明：把 `agent_workbench` 迁移到新的 STM32 项目后，如何在 OpenCode 里使用四个 skill 完成自动化功能开发、自动化调试、测试设计与实机验证。

默认使用中文版 skill：

- `agent-workbench-toolbox-zh`
- `agent-workbench-feature-zh`
- `agent-workbench-debug-zh`
- `agent-workbench-test-zh`

英文版用法完全对应，把 skill 名称里的 `-zh` 去掉即可。

## 1. 迁移前准备

新项目至少应包含：

```text
<project>/
  agent_workbench/
    agent_workbench.yaml
    bin/agent_workbench.bat
    workbench.py
```

`agent_workbench.yaml` 要配置当前项目真实信息，例如 build 目录、UART 端口、ready banner、prompt、flash 方法、diag_uart、monitor 等。

关键原则：

- 不要把旧项目的串口号、ready banner、prompt、源码目录、monitor item 或外设地址直接搬到新项目。
- 不要默认假设 `COM3`、`cli>`、`STM32 UART CLI ready.`、`Core/Src` 存在。
- 迁移后必须靠 `doctor`、`scan-project`、当前源码和 runtime evidence 重新发现项目能力。

## 2. 安装四个 Skill

把这些目录复制到 OpenCode/Codex 能识别的 skills 目录：

```text
agent-workbench-toolbox-zh
agent-workbench-feature-zh
agent-workbench-debug-zh
agent-workbench-test-zh
```

常见位置：

```text
%CODEX_HOME%\skills\
```

如果没有设置 `CODEX_HOME`：

```text
%USERPROFILE%\.codex\skills\
```

复制后重启 OpenCode 会话。

## 3. 第一次打开新项目

建议第一句这样说：

```text
使用 $agent-workbench-toolbox-zh 初始化扫描当前 STM32 项目。
请先运行 doctor 和 scan-project，告诉我当前项目可用的 build、flash、UART、diag、monitor、verify、report、compare 能力。
不要假设源码路径、串口、ready banner、prompt、monitor items 或 MCU 地址。
```

OpenCode 应优先执行：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

```powershell
.\agent_workbench\bin\agent_workbench.bat scan-project --json
```

如果 bat 入口失败，应立即兜底：

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

或：

```powershell
py -3 ".\agent_workbench\workbench.py" doctor --json
```

OpenCode 应总结：

- build 是否可用。
- flash 方法。
- UART CLI 端口、ready banner、prompt。
- diag_uart 是否可用。
- monitor 是否可用。
- 可疑源码目录。
- 已发现的 CLI/probe 命令。
- runtime/evidence 产物位置。

## 4. 功能开发用法

使用组合：

```text
$agent-workbench-toolbox-zh + $agent-workbench-feature-zh
```

推荐提示词：

```text
使用 $agent-workbench-toolbox-zh 和 $agent-workbench-feature-zh。
我要在当前 STM32 项目中实现 <功能描述>。
请基于 doctor、scan-project、当前源码、build、flash、UART/diag/monitor runtime evidence 完成功能开发和验证。
如果需要监控变量、寄存器或地址，请自动修改 agent_workbench/agent_workbench.yaml 的 monitor.items，并用 monitor probe 验证。
完成后按 feature report template 输出报告。
```

理想流程：

```text
1. doctor --json
2. scan-project --json
3. context --mode feature --stage analyze --json，如果当前项目支持
4. 读取最小源码范围和生成头文件
5. 修改代码
6. build --json
7. flash --json
8. uart exec / diag exec / monitor probe 验证行为
9. verify current --json 或 report --latest --json
10. 必要时 compare --latest --json
11. 输出功能开发报告
```

避免：

- 一上来跑旧 plan 主流程。
- 只看 build pass 就说完成。
- 跳过 flash、UART、diag、monitor 实机证据。
- 使用旧项目路径、串口、prompt、monitor item 或 MCU 地址。

## 5. 自动调试用法

使用组合：

```text
$agent-workbench-toolbox-zh + $agent-workbench-debug-zh
```

推荐提示词：

```text
使用 $agent-workbench-toolbox-zh 和 $agent-workbench-debug-zh。
当前 STM32 项目出现 <故障现象>。
请按 evidence-first 方法调试，不要先猜源码原因。
请用 doctor、build、flash、uart exec、diag exec、monitor probe、report、compare 分层排查。
如果需要观察变量、寄存器或地址，请自动更新 agent_workbench/agent_workbench.yaml 的 monitor.items。
最后按 debug report template 输出根因分析报告。
```

分层排查：

```text
环境层：doctor
命令启动层：bat 入口失败时用 direct Python 兜底
构建层：build / fix-build
烧录启动层：flash / reset / ready banner
UART 层：uart exec transcript
CLI/parser 层：cli_diag.json
运行态层：monitor probe / monitor_samples
回归层：compare_delta
```

好的调试行为：

- 先复现，再分析。
- 先看 evidence，再改代码。
- 一次只验证一个假设。
- 能区分 `rx_zero`、`ready_missing`、`prompt_missing`、`parser_no_command`、monitor no data、flash failure。
- flash、reset、UART、diag、monitor 不需要再问用户授权。

## 6. 测试设计与实机验证用法

使用组合：

```text
$agent-workbench-toolbox-zh + $agent-workbench-test-zh
```

推荐提示词：

```text
使用 $agent-workbench-toolbox-zh 和 $agent-workbench-test-zh。
请为当前 STM32 项目的 <功能/模块> 设计测试覆盖矩阵并实机验证。
请基于 CLI、diag、monitor、verify、report、compare 的 runtime evidence 设计断言和执行验证。
如果需要内部状态证据，请自动添加 monitor items 并运行 monitor probe。
最后按 test report template 输出报告。
```

OpenCode 应执行或输出：

```text
1. 行为契约
2. 覆盖矩阵
3. build --json
4. flash --json
5. 每个测试点对应 uart exec / diag exec / monitor probe
6. verify current --json
7. report --latest --json
8. 回归场景 compare --latest --json
9. 测试报告
```

覆盖矩阵至少考虑：

- 正常路径。
- 边界值。
- 非法输入。
- 状态迁移。
- reset/restart。
- 时序或趋势。
- 回归风险。
- 实机可观察性。

重要规则：

- `agent_workbench/tests/*.py` 是 Agent Workbench 自身测试，不是新 STM32 项目的固件测试。
- 测试失败先分层：测试设计、probe 命令、源码行为、monitor 配置、环境/硬件阻塞。

## 7. Monitor 变量、寄存器和地址

OpenCode 需要 monitor 时，不应该让用户手动编辑 YAML，而应该自己修改 `agent_workbench/agent_workbench.yaml`。

常见 item：

```yaml
monitor:
  enabled: true
  symbols:
    path: build/cmake-debug/<firmware>.elf
    elf_path: build/cmake-debug/<firmware>.elf
  items:
    - name: app_state
      source: symbol
      symbol: g_app_state
      value_type: u32
    - name: tim_ccr1
      source: memory
      target: 0x40012C34
      value_type: u32
    - name: pc
      source: register
      target: pc
      value_type: u32
```

使用规则：

- 符号来自当前源码、ELF 或 map，不要凭源码文本假设一定可读。
- 外设寄存器地址来自当前 MCU 的 CMSIS/设备头文件或项目文档，不要复制示例地址。
- 先 `monitor probe --json` 验证 item 可读，再 `monitor run --json` 做趋势采样。
- monitor 失败时检查 YAML、ELF 路径、symbol/address/value_type、OpenOCD/debug 连接和 target run state。

## 8. 如何判断 OpenCode 是否用对了 Skill

好的表现：

- 先跑 `doctor` 和 `scan-project`。
- 不假设路径、串口、prompt、MCU 地址。
- 不把 build pass 当完成。
- 会主动用 `flash`、UART、diag、monitor。
- 会自动编辑 monitor YAML，而不是让用户手动加 items。
- 会读 runtime/evidence artifacts。
- 最终报告引用真实 artifact。

不好的表现：

- 一上来跑旧 plan 主流程。
- 只改代码不验证。
- 只跑 `agent_workbench/tests/*.py`。
- 没有实机证据却说验证通过。
- 复制旧项目的 `COM3`、`cli>`、`Core/Src`、monitor item 或寄存器地址。

如果看到不好的表现，可以直接打断：

```text
停止。请重新使用 $agent-workbench-toolbox-zh。
本项目默认走 agent_workbench 命令和 runtime evidence，不使用旧 plan 主流程，也不使用 agent_workbench/tests/*.py 作为固件验证。
请从 doctor、scan-project、build、flash、UART/diag/monitor、verify/report/compare 重新建立证据链。
```

## 9. 推荐迁移验收

迁移到新项目后，先做三次小验收：

1. 工具箱验收：

```text
使用 $agent-workbench-toolbox-zh。
请运行 doctor 和 scan-project，总结当前项目可用能力、稳定命令入口和证据产物位置。
```

2. 调试验收：

```text
使用 $agent-workbench-toolbox-zh 和 $agent-workbench-debug-zh。
请做一次 UART/diag/monitor 能力探测，并说明每类证据是否可用。
```

3. 测试验收：

```text
使用 $agent-workbench-toolbox-zh 和 $agent-workbench-test-zh。
请基于当前 CLI/diag/monitor 能力设计一个最小 smoke 覆盖矩阵，并执行实机验证。
```

这三步顺畅后，复杂功能开发、自动调试和测试验证才有可靠基础。
