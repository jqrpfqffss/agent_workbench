# 功能开发路径

## 常规路径

1. 用 `doctor --json` 和 `scan-project --json` 发现项目。
2. 读取相关源码、生成头文件、linker/map 文件和已有 runtime evidence。
3. 找到最小修改文件集合。
4. 保持自动化依赖的稳定用户可见字符串，尤其 ready banner、prompt、help/status 命令名和约定响应前缀。
5. 生成文件存在 user code 区时，优先在安全区域修改。
6. build，小步修复，再 build。
7. flash，然后运行 UART/diag probe 触发被修改行为。
8. 功能需要内部状态、寄存器、计数器或趋势证明时，添加 monitor items。
9. 运行 verify/report/compare，并输出功能报告。

## 避免事项

- 不要凭记忆推导 timer、GPIO、ADC、DMA 或 register 参数；必须读取项目配置、生成头文件、CMSIS 头文件或现有代码。
- 不要只用 build 成功作为验证。
- OpenCode 可以修改 workbench 配置时，不要让用户手动编辑。
- 建立通过的 baseline 前，不要做大重构。

## 证据策略

- CLI 功能：UART 命令响应 + transcript。
- 协议功能：diag exchange + log/result artifact。
- 运行态功能：monitor probe/run + UART 或 diag 触发。
- 时序/趋势功能：monitor samples + 预期范围或方向。
- 回归敏感功能：latest report + compare delta。
