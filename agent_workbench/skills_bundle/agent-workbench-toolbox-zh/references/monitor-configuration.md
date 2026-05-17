# Monitor 自动配置

当功能或故障需要 UART/diag 文本之外的运行态证据时使用 monitor：计数器、状态变量、flag、控制输出、内存映射寄存器、CPU 寄存器、趋势采样等。

Codex 应自动编辑 `agent_workbench/agent_workbench.yaml` 完成 monitor 配置。不要让用户手动添加 monitor items。

## 配置检查表

运行 `monitor start --json` 前：

1. 运行 `doctor --json`，确认 monitor、ELF、OpenOCD 和 symbol image 可用。
2. 运行 `build --json`，确保 ELF 和 symbols 是最新的。
3. 确认 `monitor.symbols.path` 或 `monitor.symbols.elf_path` 指向当前 build/flash 使用的同一个 ELF。
4. 确保 `monitor.enabled: true`。
5. 只添加当前排查或验证真正需要的 items。
6. 启动采样后执行触发动作，再运行 `monitor stop --json` 和 `monitor stats --json`。

## Item 类型

全局符号：

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
```

全局结构体中的字段，使用字节 offset：

```yaml
    - name: control_error
      source: symbol
      symbol: g_control
      offset: 8
      value_type: s32
```

裸内存或外设寄存器地址：

```yaml
    - name: tim_ccr1
      source: memory
      target: 0x40012C34
      value_type: u32
```

CPU 寄存器：

```yaml
    - name: pc
      source: register
      target: pc
      value_type: u32
```

常见 `value_type`：`u32`、`s32`、`float`、`u16`、`s16`、`u8`、`s8`。

## 如何发现 items

- 优先使用当前项目里已经存在的稳定全局 `volatile` 变量、计数器、flag 和状态结构体。
- 如果关键状态只有局部变量且必须观察，做最小安全源码改动，暴露稳定命名的 debug counter 或 state mirror。
- build 后通过 ELF、map 文件或 toolchain symbol 输出确认符号存在。不要因为源码里出现过变量名就假设 symbol 可读。
- 外设寄存器地址必须从当前 MCU 的 CMSIS 头文件、生成 device header、linker map 或项目文档推导。迁移项目时禁止复用示例地址。
- CPU 寄存器只在能回答当前问题时使用，例如 `pc`、`sp` 或通用寄存器。

## 采样闭环

1. 编辑 YAML。
2. 运行 `build --json`，确保符号和 ELF 更新。
3. 运行 `monitor start --json` 或 `monitor start --reset-first --json`。
4. 用 `uart exec`、`diag exec`、`reset` 或目标事件触发行为。
5. 运行 `monitor stop --json`。
6. 运行 `monitor stats --json` 并读取 `monitor_live/monitor_samples.csv`、`monitor_samples_wide.csv`、`monitor_snapshot.csv`。

## 好的 monitor 设计

- 排查阶段 item 数量要少，通常 3 到 8 个高信号项比“全量采样”更好。
- item 名称要表达含义，例如 `motor_pwm_duty`，不要写成 `var1`。
- 至少包含一个 liveness 信号，例如 tick counter、loop counter、command counter 或 state transition counter。
- 尽量成对观察因果：命令计数 + 状态变量、输入 flag + 输出寄存器、错误码 + 重试计数。
- 趋势验证前先定义期望方向或范围，再读取样本。

## 失败处理

- symbol not found：重新 build，确认 ELF 路径，检查拼写和可见性，再查 map/symbol 输出。
- read timeout：确认 OpenOCD/debug 连接和 target run state，必要时临时缩小到单个 item。
- 一直为 0：判断是真实值、复位状态、ELF 过期、代码路径未走到，还是优化导致不可观测。
- 外设地址无效：从当前 MCU 头文件重新推导，不要复制示例。
- 样本缺失：先读 monitor artifacts 和 `doctor_report.json`，再决定是否改源码。
