# STM32 变量/寄存器/内存地址实时监控使用教程

> Agent Workbench 内置了类似 STM32CubeMonitor 的变量监控能力：通过 OpenOCD SWD/JTAG 调试接口，以 **halt → 批量读取 → resume** 轮询方式，实时采集 MCU 上的全局变量、外设寄存器和任意内存地址。

---

## 目录

1. [前置条件](#1-前置条件)
2. [基本概念](#2-基本概念)
3. [配置详解](#3-配置详解)
   - [3.1 监控全局变量（symbol）](#31-监控全局变量symbol)
   - [3.2 监控指定内存地址（memory）](#32-监控指定内存地址memory)
   - [3.3 监控外设寄存器（memory + 寄存器地址）](#33-监控外设寄存器memory--寄存器地址)
   - [3.4 监控 CPU 寄存器（register）](#34-监控-cpu-寄存器register)
4. [支持的数据类型](#4-支持的数据类型)
5. [完整配置示例](#5-完整配置示例)
6. [操作流程](#6-操作流程)
   - [6.1 启动 OpenOCD 守护进程](#61-启动-openocd-守护进程)
   - [6.2 启动 Monitor](#62-启动-monitor)
   - [6.3 查看监控状态](#63-查看监控状态)
   - [6.4 停止 Monitor](#64-停止-monitor)
7. [输出文件说明](#7-输出文件说明)
8. [工作原理](#8-工作原理)
9. [常见问题与排查](#9-常见问题与排查)
10. [高级用法](#10-高级用法)

---

## 1. 前置条件

| 依赖项 | 说明 |
|--------|------|
| **OpenOCD** | 已安装并在 PATH 中可用（`openocd --version` 能正常输出） |
| **ST-Link** | 调试器已连接到 STM32 目标板 |
| **符号映像文件** | 已编译且与当前烧录固件匹配的 `.elf` / `.axf` 文件 |
| **arm-none-eabi-nm** | 用于从符号映像中解析符号地址（交叉编译工具链自带） |
| **Python 3.7+** | 已安装 PyYAML 和 pyserial |

> ⚠️ **重要**：监控时符号映像文件必须与板上烧录的固件完全一致，否则符号地址会错位，读到错误数据。

---

## 2. 基本概念

### 监控方式

Agent Workbench 的 Monitor 采用 **CubeMonitor 标准轮询模式**：

```
┌─────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐
│  halt   │───▶│ 读取变量 │───▶│ resume  │───▶│ 等待下次 │
│  CPU    │    │ (mdw/mdb)│    │  CPU    │    │ 采样周期 │
└─────────┘    └──────────┘    └─────────┘    └──────────┘
                                                   │
                                                   ▼
                                              循环采样
```

- **halt**：暂停 CPU 执行（通常 < 1ms）
- **批量读取**：读取所有监控项的内存值
- **resume**：恢复 CPU 继续运行
- **采样间隔**：由 `sample_hz` 控制（默认 10Hz = 100ms）

### 监控源类型

| source 类型 | 说明 | 适用场景 |
|------------|------|---------|
| `symbol` | 从符号表解析变量地址 | 全局变量（如 `g_data`、`g_counter`） |
| `memory` | 直接指定内存地址 | 外设寄存器、固定 RAM 地址 |
| `register` | 读取 CPU 寄存器 | PC、SP、LR 等 ARM 核心寄存器 |

---

## 3. 配置详解

所有监控配置都在 `agent_workbench/agent_workbench.yaml` 的 `monitor` 段中。

### 3.1 监控全局变量（symbol）

**场景**：监控 C 代码中 `volatile uint32_t g_data` 这类全局变量。

**C 代码示例**：
```c
// main.c
volatile uint32_t g_data = 0;       // 需要是全局变量（非 static 或确认在符号表中）
volatile int32_t  g_temperature = 0; // 有符号也支持
volatile float    g_voltage = 0.0f;  // 浮点也支持

int main(void) {
    while (1) {
        g_data += 2;
        g_temperature = read_sensor();
        g_voltage = adc_to_voltage(ADC1->DR);
    }
}
```

**YAML 配置**：
```yaml
monitor:
  enabled: true
  items:
    - name: g_data            # 显示名称（在 CSV/JSONL 中出现）
      source: symbol          # 从符号表解析地址
      symbol: g_data          # C 代码中的变量名（必须是全局符号）
      value_type: u32         # 数据类型

    - name: temperature
      source: symbol
      symbol: g_temperature
      value_type: s32         # 有符号 32 位

    - name: voltage
      source: symbol
      symbol: g_voltage
      value_type: float       # IEEE 754 单精度浮点
```

**关键点**：
- `symbol` 字段必须与 C 代码中的**全局变量名**完全一致
- `static` 局部变量不在全局符号表中，无法直接通过名称监控（需用 `memory` + 手动查地址）
- 如果变量被编译器优化掉，需要加 `volatile` 关键字

**验证符号是否存在**：
```bash
arm-none-eabi-nm -n build/cmake-debug/serial.elf | findstr g_data
# 或者
arm-none-eabi-nm -n build/cmake-debug/serial.axf | findstr g_data
# 输出示例：200001b0 B g_data
# 200001b0 就是变量在 RAM 中的地址
```

### 3.2 监控指定内存地址（memory）

**场景**：监控已知地址的 RAM 区域或外设寄存器。

**YAML 配置**：
```yaml
monitor:
  items:
    # 监控固定 RAM 地址
    - name: ram_word
      source: memory
      target: 0x20000000       # RAM 起始地址的第一个 word
      value_type: u32

    # 监控 GPIOA 输出数据寄存器 (ODR)
    - name: GPIOA_ODR
      source: memory
      target: 0x4001080C       # STM32F103 GPIOA ODR 地址
      value_type: u32

    # 监控 ADC1 数据寄存器
    - name: ADC1_DR
      source: memory
      target: 0x4001244C       # STM32F103 ADC1_DR 地址
      value_type: u16           # ADC 数据是 16 位

    # 监控 SysTick 当前值寄存器
    - name: SysTick_VAL
      source: memory
      target: 0xE000E018       # ARM Cortex-M SysTick CVR
      value_type: u32
```

**常用 STM32F103 寄存器地址速查**：

| 寄存器 | 地址 | 说明 |
|--------|------|------|
| `GPIOA_IDR` | `0x40010808` | GPIOA 输入数据 |
| `GPIOA_ODR` | `0x4001080C` | GPIOA 输出数据 |
| `GPIOB_IDR` | `0x40010C08` | GPIOB 输入数据 |
| `GPIOB_ODR` | `0x40010C0C` | GPIOB 输出数据 |
| `GPIOC_IDR` | `0x40011008` | GPIOC 输入数据 |
| `TIM1_CNT` | `0x40012C24` | TIM1 计数器值 |
| `TIM2_CNT` | `0x40000024` | TIM2 计数器值 |
| `TIM3_CNT` | `0x40000424` | TIM3 计数器值 |
| `ADC1_DR` | `0x4001244C` | ADC1 转换结果 |
| `USART1_DR` | `0x40013804` | USART1 数据 |
| `USART2_DR` | `0x40004404` | USART2 数据 |
| `RCC_CR` | `0x40021000` | 时钟控制 |
| `SysTick_VAL` | `0xE000E018` | SysTick 当前值 |
| `DWT_CYCCNT` | `0xE0001004` | CPU 周期计数器 |

> 💡 地址可从 STM32 参考手册（RM0008）的寄存器映射表中查到。

### 3.3 监控外设寄存器（memory + 寄存器地址）

**场景**：监控 TIM、ADC、GPIO 等外设的实时状态。

```yaml
monitor:
  items:
    # 监控 TIM2 计数器 - 查看 PWM 计时
    - name: TIM2_Counter
      source: memory
      target: 0x40000024      # TIM2->CNT
      value_type: u16

    # 监控 TIM2 CCR1 - PWM 占空比捕获值
    - name: TIM2_CCR1
      source: memory
      target: 0x40000034      # TIM2->CCR1
      value_type: u32

    # 监控 DMA1 Channel1 剩余数据量
    - name: DMA1_CH1_CNDTR
      source: memory
      target: 0x4002000C      # DMA1_Channel1->CNDTR
      value_type: u16

    # 用符号名 + 偏移量访问结构体成员
    - name: cli_rx_count
      source: symbol
      symbol: cli               # CliContext cli 结构体基地址
      offset: 8                 # 假设 rx_count 在结构体偏移 8 字节处
      value_type: u32
```

### 3.4 监控 CPU 寄存器（register）

**场景**：监控 ARM Cortex-M 核心寄存器（PC、SP、LR 等）。

```yaml
monitor:
  items:
    # 程序计数器 - 查看当前执行位置
    - name: PC
      source: register
      target: pc
      value_type: u32

    # 堆栈指针 - 监控栈深度
    - name: SP
      source: register
      target: sp
      value_type: u32

    # 链接寄存器 - 查看返回地址
    - name: LR
      source: register
      target: lr
      value_type: u32

    # 通用寄存器 R0
    - name: R0
      source: register
      target: r0
      value_type: u32

    # 程序状态寄存器
    - name: xPSR
      source: register
      target: xPSR
      value_type: u32
```

**可用的 Cortex-M3 寄存器名**：
`r0`-`r12`, `sp` (r13), `lr` (r14), `pc` (r15), `xPSR`, `msp`, `psp`, `primask`, `basepri`, `faultmask`, `control`

---

## 4. 支持的数据类型

| value_type | 位宽 | 范围 | OpenOCD 命令 | 说明 |
|-----------|------|------|-------------|------|
| `u32` | 32-bit | 0 ~ 4,294,967,295 | `mdw` | 无符号 32 位整数（默认） |
| `s32` | 32-bit | -2,147,483,648 ~ 2,147,483,647 | `mdw` | 有符号 32 位整数 |
| `u16` | 16-bit | 0 ~ 65,535 | `mdh` | 无符号 16 位整数 |
| `s16` | 16-bit | -32,768 ~ 32,767 | `mdh` | 有符号 16 位整数 |
| `u8` | 8-bit | 0 ~ 255 | `mdb` | 无符号 8 位整数 |
| `s8` | 8-bit | -128 ~ 127 | `mdb` | 有符号 8 位整数 |
| `float` | 32-bit | IEEE 754 | `mdw` | 单精度浮点数 |

---

## 5. 完整配置示例

```yaml
monitor:
  # 总开关
  enabled: true

  # 采样频率（Hz）。10 = 每 100ms 采一次
  # 注意：频率越高，halt/resume 对固件的干扰越大
  sample_hz: 10

  # 环形缓冲区大小（每个监控项）
  ring_size: 2000

  # 导出快照的间隔（秒）
  export_interval_sec: 3

  # OpenOCD 连接配置
  openocd:
    host: 127.0.0.1
    port: 4444
    timeout_sec: 2.0

  # 符号解析用的映像文件（必须与烧录固件一致）
  symbols:
    path: build/cmake-debug/serial.elf
    elf_path: build/cmake-debug/serial.elf

  # 监控项列表
  items:
    # ─── 全局变量监控 ───
    - name: g_data
      source: symbol
      symbol: g_data
      value_type: u32

    - name: g_temperature
      source: symbol
      symbol: g_temperature
      value_type: s32

    - name: g_voltage
      source: symbol
      symbol: g_voltage
      value_type: float

    # ─── 外设寄存器监控 ───
    - name: GPIOA_ODR
      source: memory
      target: 0x4001080C
      value_type: u32

    - name: TIM2_CNT
      source: memory
      target: 0x40000024
      value_type: u16

    - name: ADC1_DR
      source: memory
      target: 0x4001244C
      value_type: u16

    # ─── CPU 寄存器监控 ───
    - name: PC
      source: register
      target: pc
      value_type: u32

    - name: SP
      source: register
      target: sp
      value_type: u32
```

---

## 6. 操作流程

### 6.1 启动 OpenOCD 守护进程

Monitor 需要通过 OpenOCD telnet 接口（默认端口 4444）与目标通信。

```bash
# 启动 OpenOCD 守护进程
.\agent_workbench.bat openocd start --json

# 检查状态
.\agent_workbench.bat openocd status --json
```

**期望输出**：
```json
{"summary": "openocd started pid=XXXX (127.0.0.1:4444)"}
```

### 6.2 启动 Monitor

```bash
# 启动监控（后台守护进程模式）
.\agent_workbench.bat monitor start --json
```

**期望输出**：
```json
{"summary": "monitor started pid=XXXX, out=...\monitor_live"}
```

Monitor 启动后会：
1. 从符号映像文件解析所有 `source: symbol` 项的地址
2. 连接 OpenOCD telnet 端口
3. 确保目标处于运行状态（发送 `resume`）
4. 按 `sample_hz` 频率循环执行 halt → 读取 → resume
5. 将数据实时写入 CSV 和 JSONL 文件

### 6.3 查看监控状态

```bash
.\agent_workbench.bat monitor status --json
```

### 6.4 停止 Monitor

```bash
.\agent_workbench.bat monitor stop --json
```

停止后：
- 目标会被恢复到运行状态
- 最终快照会写入 `monitor_snapshot.csv`
- 停止事件记录到 `monitor_session.jsonl`

### 6.5 导出数据

```bash
# 导出监控数据到指定路径
.\agent_workbench.bat monitor export --dst path/to/output.csv --json
```

---

## 7. 输出文件说明

所有输出文件位于 `agent_workbench/runtime/monitor_live/` 目录：

### `monitor_session.jsonl`

会话元数据，记录启动/停止事件和监控项描述：

```json
{
  "ts": "2026-04-29T14:32:56.000+00:00",
  "event": "monitor_start",
  "items": [
    {
      "name": "g_data",
      "source": "symbol",
      "value_type": "u32",
      "width_bits": 32,
      "resolved_address": "0x200001b0",
      "symbol": "g_data"
    }
  ]
}
```

### `monitor_samples.csv`

主数据文件，每行一个采样点：

```csv
ts,item,value,ok,message
2026-04-29T14:32:56.747+00:00,g_data,12084,1,
2026-04-29T14:32:56.852+00:00,g_data,12086,1,
2026-04-29T14:32:56.963+00:00,g_data,12088,1,
```

| 列 | 说明 |
|----|------|
| `ts` | UTC 时间戳（ISO 8601 格式） |
| `item` | 监控项名称 |
| `value` | 读取到的值（已按 value_type 转换） |
| `ok` | 1=成功, 0=失败 |
| `message` | 失败时的错误信息 |

### `monitor_samples.jsonl`

与 CSV 相同的数据，JSON Lines 格式（便于程序解析）：

```json
{"ts": "2026-04-29T14:32:56.747+00:00", "item": "g_data", "value": 12084, "ok": true, "message": ""}
```

### `monitor_snapshot.csv`

环形缓冲区快照，每 `export_interval_sec` 秒刷新一次：

```csv
item,index,ts,value,ok,message
g_data,0,2026-04-29T14:32:56.747+00:00,12084,1,
g_data,1,2026-04-29T14:32:56.852+00:00,12086,1,
```

---

## 8. 工作原理

### 架构图

```
┌─────────────────────────────────────────────────────┐
│                  Host PC (Python)                     │
│                                                       │
│  ┌─────────────┐    ┌──────────────┐                  │
│  │ YAML 配置   │───▶│ MonitorEngine│                  │
│  │ (items列表) │    │              │                  │
│  └─────────────┘    │  ┌─────────┐ │                  │
│                     │  │符号解析 │ │  arm-none-eabi-nm │
│  ┌─────────────┐    │  │ ELF→地址│ │◀──── serial.elf  │
│  │ CSV/JSONL   │◀───│  └─────────┘ │                  │
│  │ 输出文件    │    │              │                  │
│  └─────────────┘    │  ┌─────────┐ │                  │
│                     │  │OpenOCD  │ │                  │
│                     │  │ Client  │ │                  │
│                     │  └────┬────┘ │                  │
│                     └───────┼──────┘                  │
│                             │ Telnet (port 4444)      │
└─────────────────────────────┼─────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  OpenOCD Daemon    │
                    │  (SWD/JTAG)       │
                    └─────────┬─────────┘
                              │ ST-Link
                    ┌─────────▼─────────┐
                    │    STM32 MCU      │
                    │  ┌──────────────┐ │
                    │  │ 0x200001b0:  │ │
                    │  │ g_data = 42  │ │
                    │  └──────────────┘ │
                    └───────────────────┘
```

### 采样时序

```
时间轴 ──────────────────────────────────────────▶

MCU运行: ████████░████████░████████░████████░█████
               ↑        ↑        ↑        ↑
             halt     halt     halt     halt
             读取     读取     读取     读取
             resume   resume   resume   resume

                 ~100ms     ~100ms     ~100ms
              (sample_hz=10)
```

**halt 窗口时间**：对于少量监控项（1-5个），每次 halt 持续约 0.5-2ms，对固件实时性影响极小。

### 符号地址解析流程

```
1. 读取符号映像    ─▶  arm-none-eabi-nm -n serial.elf
2. 解析输出    ─▶  "200001b0 B g_data" → {g_data: 0x200001b0}
3. 配置匹配    ─▶  item.symbol = "g_data" → address = 0x200001b0
4. OpenOCD读取 ─▶  mdw 0x200001b0 1 → "0x200001b0: 0000002a"
5. 解析值      ─▶  0x2a = 42 (u32)
```

---

## 9. 常见问题与排查

### Q1: 监控值始终不变

**原因**：CPU 被 halt 后未 resume，固件停止运行。

**排查**：
```bash
# 检查是否用的最新 monitor_service.py（必须包含 halt/resume 循环）
# 搜索关键代码行
findstr "self.openocd.halt()" agent_workbench\core\monitor_service.py
findstr "self.openocd.resume()" agent_workbench\core\monitor_service.py
```

**解决**：确保 `monitor_service.py` 的 `run()` 方法包含 halt → read → resume 循环。

### Q2: "symbol not found in symbol image" 错误

**原因**：
- 变量名拼写错误
- 变量被声明为 `static`（不在全局符号表中）
- 编译器优化掉了变量

**排查**：
```bash
# 查看符号映像中是否存在该符号
arm-none-eabi-nm -n build/cmake-debug/serial.elf | findstr "变量名"
```

**解决**：
- 确认变量拼写一致
- 将 `static` 变量改为全局变量
- 添加 `volatile` 关键字防止优化

### Q3: "openocd socket not connected" 错误

**原因**：OpenOCD 守护进程未启动或连接断开。

**解决**：
```bash
.\agent_workbench.bat openocd start --json
.\agent_workbench.bat openocd status --json
```

### Q4: 烧录后监控值异常

**原因**：符号映像文件与烧录固件不匹配，符号地址错位。

**解决**：
1. 重新编译：`.\agent_workbench.bat build --json`
2. 重新烧录：`.\agent_workbench.bat flash --json`
3. 重启 OpenOCD：`.\agent_workbench.bat openocd stop --json` → `.\agent_workbench.bat openocd start --json`
4. 重启 Monitor：`.\agent_workbench.bat monitor stop --json` → `.\agent_workbench.bat monitor start --json`

### Q5: PermissionError 文件锁定

**原因**：CSV 文件被其他程序（VS Code 预览等）锁定。

**解决**：
- 关闭所有打开该文件的编辑器/程序
- 或在 `monitor start` 前手动删除旧文件：
```bash
del /f agent_workbench\runtime\monitor_live\monitor_samples.csv
```

### Q6: Monitor daemon 启动后立即变为 stale

**排查步骤**：
```bash
# 1. 先停止旧的 monitor
.\agent_workbench.bat monitor stop --json

# 2. 确认 OpenOCD 在运行
.\agent_workbench.bat openocd status --json

# 3. 直接前台运行查看错误
"C:\Users\Administrator\AppData\Local\Programs\Python\Python38\python.exe" ^
  agent_workbench\workbench.py monitor run ^
  --config agent_workbench\agent_workbench.yaml ^
  --out-dir agent_workbench\runtime\monitor_live
```

### Q7: 采样频率设多少合适？

| 场景 | 推荐 sample_hz | 说明 |
|------|---------------|------|
| 慢变量（温度、状态） | 1-5 | 对固件几乎无影响 |
| 中速变量（计数器） | 10 | 默认值，平衡精度和干扰 |
| 快速信号（PWM占空比） | 20-50 | 注意 halt 频率对实时性的影响 |
| 调试定位（PC/SP） | 5-10 | 用于追踪执行流程 |

---

## 10. 高级用法

### 10.1 使用偏移量访问结构体成员

如果全局变量是一个结构体，可以用 `symbol` + `offset` 访问特定成员：

```c
// C 代码
typedef struct {
    uint32_t count;      // 偏移 0
    int16_t  value;      // 偏移 4
    uint8_t  flags;      // 偏移 6
    uint8_t  status;     // 偏移 7
} SensorData;

SensorData g_sensor;
```

```yaml
monitor:
  items:
    - name: sensor_count
      source: symbol
      symbol: g_sensor
      offset: 0            # count 字段
      value_type: u32

    - name: sensor_value
      source: symbol
      symbol: g_sensor
      offset: 4            # value 字段
      value_type: s16

    - name: sensor_flags
      source: symbol
      symbol: g_sensor
      offset: 6            # flags 字段
      value_type: u8
```

### 10.2 同时监控多个变量

```yaml
monitor:
  items:
    - name: pwm_duty
      source: symbol
      symbol: g_pwm_duty
      value_type: u16

    - name: adc_raw
      source: symbol
      symbol: g_adc_raw
      value_type: u16

    - name: motor_speed
      source: symbol
      symbol: g_motor_rpm
      value_type: s32

    - name: error_code
      source: symbol
      symbol: g_error
      value_type: u8
```

> 💡 监控项越多，每次 halt 持续时间越长。建议总数不超过 10-15 个。

### 10.3 与 Session/Verify 流程集成

Monitor 会在 `session` 和 `verify` 流程中自动启动：

```bash
# 完整验证流程（包含 doctor + build + flash + monitor）
.\agent_workbench.bat verify current --json
```

在 `workflow.observe_seconds` 期间，Monitor 会持续采集数据，最终输出到证据报告中。

### 10.4 用 Python 脚本分析监控数据

```python
import csv
from pathlib import Path

# 读取 CSV 数据
data = []
with open("agent_workbench/runtime/monitor_live/monitor_samples.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["ok"] == "1":
            data.append({
                "ts": row["ts"],
                "item": row["item"],
                "value": float(row["value"])
            })

# 分析 g_data
g_data_values = [d["value"] for d in data if d["item"] == "g_data"]
print(f"样本数: {len(g_data_values)}")
print(f"最小值: {min(g_data_values)}")
print(f"最大值: {max(g_data_values)}")
print(f"平均值: {sum(g_data_values)/len(g_data_values):.1f}")
print(f"唯一值: {len(set(g_data_values))}")
```

---

## 附录：与 STM32CubeMonitor 的对比

| 特性 | Agent Workbench Monitor | STM32CubeMonitor |
|------|------------------------|------------------|
| 调试接口 | OpenOCD (SWD/JTAG) | ST-Link (SWD) |
| 读取方式 | halt → mdw → resume | halt → read → resume |
| 配置方式 | YAML 文本文件 | Node-RED 图形界面 |
| 符号解析 | arm-none-eabi-nm | 内置符号映像解析 |
| 输出格式 | CSV + JSONL | CSV + 图表 |
| 实时图表 | 无（需外部工具） | 内置 |
| 自动化集成 | ✅ 命令行 + CI/CD | ❌ 需手动操作 |
| AI Agent 集成 | ✅ JSON 输出 | ❌ |
| 适用场景 | 自动化验证、Agent 闭环 | 手动调试、可视化 |

---

*文档生成时间：2026-04-29 | 适用版本：Agent Workbench v1.x*
