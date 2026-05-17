# 功能开发路径

## 常规路径

1. 用 `doctor --json` 发现当前项目配置和可用能力。
2. 读取相关源码、生成头文件、linker/map 文件、ELF symbols 和已有 runtime evidence。
3. 找到最小修改文件集合。
4. 保持自动化依赖的稳定用户可见字符串，尤其 ready banner、prompt、help/status 命令名和约定响应前缀。
5. 生成文件存在 USER CODE 区时，优先在安全区域修改。
6. `build --json`，失败时 `fix-build --json`，小步修复后再 build。
7. 需要板上证据时 `flash --json`，然后运行 UART/diag probe 触发被修改行为。
8. 功能需要内部状态、寄存器、计数器或趋势证明时，添加 monitor items 并采样。
9. 需要远端 Linux/覆盖率/远程设备证据时，运行 remote-dt。
10. 输出功能报告，列出真实命令、exit_code 和 artifact。

## 避免事项

- 不要凭记忆推导 timer、GPIO、ADC、DMA 或 register 参数；必须读取项目配置、生成头文件、CMSIS 头文件或现有代码。
- 不要只用 build 成功作为验证。
- 可以修改 workbench 配置时，不要让用户手动编辑 monitor items。
- 建立通过的 baseline 前，不要做大重构。
- 不要调用 README 中已经删除的旧命令。

## 证据策略

- CLI 功能：UART 命令响应 + transcript。
- 协议功能：diag exchange + result artifact。
- 运行态功能：monitor samples/stats + UART 或 diag 触发。
- 时序/趋势功能：monitor samples + 预期范围或方向。
- 远端流水线：remote-dt result/summary/logs。
