from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .openocd_client import OpenOcdClient, OpenOcdConfig
from .openocd_service import start_openocd_daemon, stop_openocd_daemon
from .utils import command_exists, command_head, render_template, utc_now_iso, write_json


_CLI_STATS_SYMBOL = "DebugCliStats"
_CLI_STATS_WORDS = 14


def _load_symbols(cfg: dict) -> dict[str, int]:
    elf_path = Path(cfg["project"]["artifact_elf_path"])
    nm_command = cfg["tools"].get("symbols_nm", "arm-none-eabi-nm")
    if not elf_path.exists():
        return {}
    try:
        output = subprocess.check_output([nm_command, "-n", str(elf_path)], stderr=subprocess.STDOUT, text=True)
    except Exception:
        return {}
    symbols: dict[str, int] = {}
    for line in output.splitlines():
        parts = line.strip().split()
        if len(parts) < 3:
            continue
        try:
            symbols[parts[2]] = int(parts[0], 16)
        except ValueError:
            continue
    return symbols


def _decode_text(words: list[int], byte_count: int) -> str:
    data = bytearray()
    for word in words:
        data.extend(int(word).to_bytes(4, byteorder="little", signed=False))
    return data[:byte_count].split(b"\x00", 1)[0].decode("utf-8", errors="replace")


def _classify_failure(stats: dict[str, Any] | None, saw_ready: bool, saw_prompt: bool, timeout_commands: list[str]) -> dict[str, str]:
    if stats is None:
        return {
            "code": "diag_unavailable",
            "summary": "CLI diagnostics unavailable",
            "detail": "OpenOCD or DebugCliStats symbol could not be read.",
        }
    if int(stats.get("rx_bytes", 0)) == 0:
        return {
            "code": "rx_zero",
            "summary": "Board did not receive UART bytes",
            "detail": "Check COM port mapping, RX/TX wiring, and whether the configured UART is the active CLI path.",
        }
    if int(stats.get("rx_bytes", 0)) > 0 and int(stats.get("cmd_ok", 0)) == 0:
        return {
            "code": "parser_no_command",
            "summary": "Board received data but did not execute commands",
            "detail": "Check line endings, command tokenization, and CLI parser state.",
        }
    if int(stats.get("cmd_ok", 0)) > 0 and timeout_commands:
        return {
            "code": "tx_or_host_rx",
            "summary": "Commands executed but the host did not capture the response",
            "detail": "Check USART3 TX wiring, USB-TTL adapter state, and host receive buffering.",
        }
    if not saw_ready:
        return {
            "code": "ready_missing",
            "summary": "CLI ready banner missing",
            "detail": "Target did not emit the expected boot handshake after reset.",
        }
    if not saw_prompt:
        return {
            "code": "prompt_missing",
            "summary": "CLI prompt missing",
            "detail": "Responses were seen but the CLI prompt was not emitted.",
        }
    return {
        "code": "unknown",
        "summary": "CLI failure requires manual review",
        "detail": "Inspect cli_transcript.log and cli_diag.json together for the full timeline.",
    }


def _openocd_client(cfg: dict) -> OpenOcdClient:
    openocd_cfg = cfg["tools"]["openocd"]
    return OpenOcdClient(
        OpenOcdConfig(
            host=openocd_cfg.get("host", "127.0.0.1"),
            port=int(openocd_cfg.get("telnet_port", 4444)),
            timeout_sec=float(openocd_cfg.get("startup_wait_sec", 3.0)),
        )
    )


def collect_cli_diag(
    cfg: dict,
    output_path: Path,
    *,
    saw_ready: bool,
    saw_prompt: bool,
    timeout_commands: list[str],
) -> Path:
    openocd_cfg = cfg["tools"]["openocd"]
    openocd_command = render_template(openocd_cfg.get("daemon_cmd", ""), cfg["template_values"])
    payload: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "symbol": _CLI_STATS_SYMBOL,
        "saw_ready": saw_ready,
        "saw_prompt": saw_prompt,
        "timeout_commands": timeout_commands,
        "openocd": {
            "host": openocd_cfg.get("host", "127.0.0.1"),
            "port": int(openocd_cfg.get("telnet_port", 4444)),
            "command": command_head(openocd_command) or "missing",
        },
        "status": "error",
    }

    if not command_exists(openocd_command):
        payload["error"] = f"openocd command unavailable: {command_head(openocd_command) or 'missing'}"
        payload["classification"] = _classify_failure(None, saw_ready, saw_prompt, timeout_commands)
        return write_json(output_path, payload)

    symbols = _load_symbols(cfg)
    address = symbols.get(_CLI_STATS_SYMBOL)
    if address is None:
        payload["error"] = f"symbol not found in ELF: {_CLI_STATS_SYMBOL}"
        payload["classification"] = _classify_failure(None, saw_ready, saw_prompt, timeout_commands)
        return write_json(output_path, payload)

    payload["symbol_address"] = f"0x{address:08x}"

    started_message = start_openocd_daemon(cfg)
    payload["openocd"]["startup_message"] = started_message
    stop_when_done = "started pid=" in started_message

    client = _openocd_client(cfg)
    try:
        client.connect()
        try:
            payload["openocd"]["halt_output"] = client.halt().strip()
        except Exception as exc:
            payload["openocd"]["halt_error"] = str(exc)
        words = client.read_mem_words(address, _CLI_STATS_WORDS)
        payload["raw_words"] = [f"0x{word:08x}" for word in words]
        stats = {
            "rx_bytes": int(words[0]),
            "rx_lines": int(words[1]),
            "cmd_ok": int(words[2]),
            "cmd_err": int(words[3]),
            "rx_overflow": int(words[4]),
            "uart_error": int(words[5]),
            "last_cmd": _decode_text(words[6:], 32),
        }
        payload["stats"] = stats
        payload["classification"] = _classify_failure(stats, saw_ready, saw_prompt, timeout_commands)
        payload["status"] = "ok"
        try:
            payload["openocd"]["resume_output"] = client.resume().strip()
        except Exception as exc:
            payload["openocd"]["resume_error"] = str(exc)
    except Exception as exc:
        payload["error"] = str(exc)
        payload["classification"] = _classify_failure(None, saw_ready, saw_prompt, timeout_commands)
    finally:
        client.close()
        if stop_when_done:
            payload["openocd"]["shutdown_message"] = stop_openocd_daemon(cfg)

    return write_json(output_path, payload)
