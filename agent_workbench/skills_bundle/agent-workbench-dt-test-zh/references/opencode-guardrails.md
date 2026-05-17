# OpenCode 执行护栏

## 推荐调用提示

```text
使用 $agent-workbench-dt-test-zh。
请为当前 STM32 项目的 <模块/功能> 编写 DT 测试用例，并接入 remote-dt 执行入口。
本 skill 只允许使用五条命令：remote-dt build/execute/coverage/pipeline/pull-logs，且必须加 --json。
不要把 agent_workbench/tests/*.py 当作固件测试。
如果 remote_dt 未启用或远端同步无法确认，请继续完成用例设计/本地改动，但把远端验证标为 blocked。
最终报告列出实际 remote-dt 命令、exit_code、dt_remote_result/summary/log/coverage artifact。
```

## 代理执行顺序

1. 读取 `agent_workbench/agent_workbench.yaml` 的 `remote_dt` 配置和已有 remote-dt artifacts。
2. 读取已有远端脚本、DT 用例入口和用户需求。
3. 设计 DT case matrix。
4. 修改 DT 用例、远端脚本或覆盖率配置。
5. 选择并运行一条 remote-dt 命令：`build`、`execute`、`coverage`、`pipeline` 或 `pull-logs`。
6. 读取 remote-dt artifacts。
7. 报告结论。

## 报告最低字段

```text
结论：pass/fail/blocked
DT 用例：<case id, target, verdict>
实际执行：<remote-dt command, exit_code, artifact>
远端证据：<dt_remote_result.json, dt_remote_summary.md, logs/dt_*.log, coverage>
改动：<文件和要点>
未执行/阻塞：<原因>
```
