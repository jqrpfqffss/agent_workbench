agent_workbench Continue Prompt Files

这套文件是 Continue 的标准 prompt files。
Continue 会把 `.prompt` 文件自动当成 slash commands。

建议入口：

1. 当前 serial 项目直接验证
   `/awb-serial-verify`

2. 通用自动化入口
   `/awb-general`

3. 通用自动化调试
   `/awb-debug`

4. 通用自动化测试
   `/awb-test`

5. 通用功能实现与验证
   `/awb-feature`

6. DeepSeek 专版
   `/awb-ds-general`
   `/awb-ds-debug`
   `/awb-ds-test`
   `/awb-ds-feature`

7. Qwen 专版
   `/awb-qwen-general`
   `/awb-qwen-debug`
   `/awb-qwen-test`
   `/awb-qwen-feature`

8. 低上下文阶段流
   `/awb-stage`

使用示例：

- `/awb-debug agent_workbench/tasks/cli_automation_regression.yaml`
- `/awb-test agent_workbench/tasks/cli_automation_regression.yaml`
- `/awb-feature agent_workbench/tasks/add_version_cli.yaml`
