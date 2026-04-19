---
description: 烧录并复位硬件（不跑测试）
---

# /flash-reset 命令

1. 先确认 build 产物存在:
   ```
   cmd /c ".\agent_workbench.bat doctor --json"
   ```
   检查 `artifact_elf` 检查项是 ok。

2. 征询用户: "即将烧录 {project_name}，是否继续？(yes/no)"

3. 用户同意后:
   ```
   cmd /c ".\agent_workbench.bat flash --method openocd_cmd --json"
   ```

4. 检查返回 JSON 的 `exit_code`:
   - 0: 成功，输出"flash ok, reset 完成"
   - 非 0: 列出 stderr 末尾 20 行并停下
