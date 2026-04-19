# 错误恢复指引

## 编译失败

1. 先读取 `errors[0]`
2. 优先修复第一条 `error`，不要同时改很多点
3. 如果当前 step 提供了 `retry_command`，先运行 `fix-build --json`
4. 读取 `suggested_fixes[0].fix.action_type`
5. 按 `target_files`、`target_region`、`code` 落最小修复
6. 修复后重新运行 `build --json`
7. 同一步骤最多连续重试 3 次

## UART CLI 失败

1. 查看 `diagnosis.summary`
2. 再看 `cli_transcript.log` 前几行
3. 优先检查 ready banner `STM32 UART CLI ready.` 与 prompt `cli>` 是否仍然存在

## flash 失败

1. 不要反复重试超过 3 次
2. 先确认用户是否允许继续操作硬件
3. 如果是工具链问题，记录阻塞并停止
