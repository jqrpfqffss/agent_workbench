---
description: 读取最新 build.log 并生成修复建议
---

# /fix-build 命令

当用户输入 `/fix-build` 时：

1. 运行:
   ```
   cmd /c ".\agent_workbench.bat fix-build --json"
   ```

2. 读取返回 JSON 的 `fixes` 数组，每项含：
   - `file`: 错误文件路径
   - `line`: 错误行号
   - `message`: 原始错误信息
   - `suggested_change`: 建议修改

3. 按行把建议展示给用户：
   ```
   发现 3 处编译错误:

   [1] Core/Src/main.c:112
       错误: 'htim1' undeclared
       建议: 在 Core/Src/main.c 顶部加 `extern TIM_HandleTypeDef htim1;`

   [2] ...
   ```

4. 询问："是否自动应用所有建议？(yes/select/no)"

5. `yes`: 用 edit 工具依次应用；每次 edit 后立刻 `build --json` 看是否减少错误
   `select`: 让用户选择应用哪几项
   `no`: 停下来

6. 全部应用后重新 build，如果还有错误递归调用 /fix-build，最多 3 轮
