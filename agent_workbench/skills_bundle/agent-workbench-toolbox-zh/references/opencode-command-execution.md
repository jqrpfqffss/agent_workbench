# OpenCode 命令执行规则

当 OpenCode 执行 workbench 命令失败，或者示例里还出现旧的 wrapper 写法时，读取本文件。

## 优先形式

从仓库根目录运行：

```powershell
.\agent_workbench\bin\agent_workbench.bat doctor --json
```

这样写的原因：

- 相对路径本身没有被引号包住，PowerShell 会把它当作可执行命令，而不是字符串。
- 内层 bat 会解析 Python 解释器和 `workbench.py`。
- 避免 `cmd /c` 额外引号层；这层在 OpenCode 实际会话里经常解析失败。

注意：下面这种写法是错误的，因为它只是一个字符串后面跟参数：

```powershell
".\agent_workbench\bin\agent_workbench.bat" doctor --json
```

如果必须给命令路径加引号，就必须加调用操作符 `&`：

```powershell
& ".\agent_workbench\bin\agent_workbench.bat" doctor --json
```

## 兜底形式

如果 bat 形式因为引号或启动器问题失败，改用：

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

如果 `python` 不在 PATH，再试：

```powershell
py -3 ".\agent_workbench\workbench.py" doctor --json
```

所有子命令都按同样规则替换。

## 规则

- 每次 shell 调用只运行一条命令。
- 命令支持 `--json` 时必须加。
- 不要在 OpenCode 里用 `;`、`&&`、`|` 串联命令，除非用户明确要求 shell 组合。
- 不要随意切到底层无关脚本；直接 Python 兜底仍然是同一个 `agent_workbench` 公共 CLI。
- 如果 bat 和 Python 形式都失败，把精确命令、exit code、stderr 作为环境阻塞报告。
