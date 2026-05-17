# 命令执行规则

当 workbench 命令启动失败、PowerShell 引号行为异常，或旧示例里出现 wrapper 写法时读取本文件。

## 优先形式

从仓库根目录运行：

```powershell
./agent_workbench/bin/agent_workbench.bat doctor --json
```

这会通过内层 batch 解析 Python 和 `workbench.py`，并保持路径相对当前仓库。

不要写成：

```powershell
"./agent_workbench/bin/agent_workbench.bat" doctor --json
```

这在 PowerShell 中只是字符串后面跟参数。若命令路径必须加引号，使用调用操作符：

```powershell
& "./agent_workbench/bin/agent_workbench.bat" doctor --json
```

## 兜底形式

如果 batch 入口因启动器或引号失败，改用同一个公共 CLI 的 Python 入口：

```powershell
python ".\agent_workbench\workbench.py" doctor --json
```

如果 `python` 不在 PATH，再试：

```powershell
py -3 ".\agent_workbench\workbench.py" doctor --json
```

所有子命令按同样规则替换，例如把 `doctor --json` 换成 `build --json`。

## 规则

- 每次 shell 调用只运行一条 workbench 命令。
- 命令支持 `--json` 时必须加。
- 不用 `cmd /c` 包装 workbench 命令，除非项目本身明确要求。
- launcher 失败只重试 direct Python 一次；仍失败就把精确命令、exit code、stderr 作为环境阻塞报告。
