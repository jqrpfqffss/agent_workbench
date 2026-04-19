from __future__ import annotations

from dataclasses import dataclass

from .utils import split_command


_KNOWN_COMMANDS = {
    "doctor",
    "build",
    "flash",
    "reset",
    "uart",
    "diag",
    "monitor",
    "openocd",
    "session",
    "test",
    "compare",
    "report",
    "init-vscode",
    "init-continue-rules",
    "context",
    "verify",
    "plan",
    "parse-errors",
    "scan-project",
}


@dataclass
class PsExecRequest:
    argv: list[str]
    normalized_text: str


def _normalize_token(token: str) -> str:
    stripped = token.strip()
    if not stripped:
        return stripped
    if "/" in stripped or "\\" in stripped or stripped.endswith((".yaml", ".yml", ".md", ".log", ".json")):
        return stripped.replace("\\", "/")
    return stripped


def normalize_ps_exec_command(command_text: str) -> PsExecRequest:
    tokens = [_normalize_token(token) for token in split_command(command_text) if str(token).strip()]
    if not tokens:
        raise RuntimeError("ps-exec requires a non-empty command")

    launcher_heads = {".\\agent_workbench.bat", "./agent_workbench.bat", "agent_workbench.bat"}
    if tokens[0].lower() in launcher_heads:
        tokens = tokens[1:]
    if not tokens:
        raise RuntimeError("ps-exec requires a workbench subcommand after agent_workbench.bat")

    command = tokens[0]
    if command == "cmd":
        raise RuntimeError("ps-exec expects a simplified workbench command, not a nested cmd /c wrapper")
    if command == "ps-exec":
        raise RuntimeError("ps-exec cannot wrap itself")
    if command not in _KNOWN_COMMANDS:
        raise RuntimeError(f"unsupported ps-exec command: {command}")

    if tokens[:2] == ["uart", "exec"] and len(tokens) > 2 and "--command" not in tokens and "--script" not in tokens:
        uart_commands = tokens[2:]
        tokens = ["uart", "exec"]
        for item in uart_commands:
            tokens.extend(["--command", item])

    if "--json" not in tokens:
        tokens.append("--json")
    return PsExecRequest(argv=tokens, normalized_text=" ".join(tokens))
