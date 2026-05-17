from __future__ import annotations

import re
import socket
import time
from dataclasses import dataclass


PROMPT = b"> "

@dataclass
class OpenOcdConfig:
    host: str = "127.0.0.1"
    port: int = 4444
    timeout_sec: float = 2.0
    post_command_drain_sec: float = 0.0


class OpenOcdClient:
    def __init__(self, cfg: OpenOcdConfig):
        self.cfg = cfg
        self.sock: socket.socket | None = None

    def connect(self) -> None:
        self.sock = socket.create_connection((self.cfg.host, self.cfg.port), timeout=self.cfg.timeout_sec)
        self.sock.settimeout(self.cfg.timeout_sec)
        self._read_until_prompt()

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def _read_until_prompt(self) -> str:
        if self.sock is None:
            raise RuntimeError("openocd socket not connected")
        data = bytearray()
        while True:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            data.extend(chunk)
            if data.endswith(PROMPT):
                break
        return data.decode(errors="ignore")

    def _drain_pending(self) -> None:
        """Read and discard any leftover / asynchronous data sitting in the
        socket receive buffer.  This prevents stale halt-notification lines
        (xPSR, pc, msp) from leaking into the next command's response."""
        if self.sock is None:
            return
        self.sock.setblocking(False)
        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
        except (BlockingIOError, OSError):
            pass
        finally:
            self.sock.settimeout(self.cfg.timeout_sec)

    def command(self, cmd: str) -> str:
        if self.sock is None:
            raise RuntimeError("openocd socket not connected")
        self.sock.sendall((cmd.strip() + "\n").encode())
        return self._read_until_prompt()

    def run_commands(self, commands: list[str]) -> list[str]:
        outputs: list[str] = []
        for command in commands:
            text = str(command).strip()
            if not text:
                continue
            outputs.append(self.command(text))
        return outputs

    def halt(self) -> str:
        resp = self.command("halt")
        if self.cfg.post_command_drain_sec > 0:
            time.sleep(self.cfg.post_command_drain_sec)
        self._drain_pending()
        return resp

    def resume(self) -> str:
        resp = self.command("resume")
        if self.cfg.post_command_drain_sec > 0:
            time.sleep(self.cfg.post_command_drain_sec)
        self._drain_pending()
        return resp

    def read_register(self, register_name: str) -> int:
        output = self.command(f"reg {register_name}")
        match = re.search(r"0x([0-9a-fA-F]+)", output)
        if not match:
            raise RuntimeError(f"cannot parse register output: {output}")
        return int(match.group(1), 16)

    def read_mem_word(self, address: int) -> int:
        return self.read_mem_words(address, 1)[0]

    def read_mem_words(self, address: int, count: int) -> list[int]:
        return self.read_mem(address, count, width_bits=32)

    def read_mem_value(self, address: int, width_bits: int = 32) -> int:
        return self.read_mem(address, 1, width_bits=width_bits)[0]

    def read_mem(self, address: int, count: int, width_bits: int = 32) -> list[int]:
        if width_bits == 8:
            command = "mdb"
            max_digits = 2
        elif width_bits == 16:
            command = "mdh"
            max_digits = 4
        elif width_bits == 32:
            command = "mdw"
            max_digits = 8
        else:
            raise ValueError(f"unsupported memory width: {width_bits}")
        output = self.command(f"{command} 0x{address:08x} {count}")
        return _parse_memory_values(output, count, max_digits=max_digits)


# Validates that the portion before the first ':' ends with a hex memory
# address (e.g. "0x200001b0").  This rejects halt-notification lines like
# "xPSR: 0x01000000 pc: 0x080015c6 msp: 0x20004fe8" where the LHS
# before ':' is "xPSR" — clearly not a hex address.
# We intentionally do NOT anchor with ^ because OpenOCD telnet may
# prepend invisible control characters (e.g. \x1a) to the line.
_ADDR_SUFFIX_RE = re.compile(r"0x[0-9a-fA-F]+\s*$")


def _parse_memory_values(output: str, count: int, max_digits: int) -> list[int]:
    if count < 1:
        return []
    token_re = re.compile(rf"[0-9a-fA-F]{{1,{max_digits}}}")
    values: list[int] = []
    for line in output.splitlines():
        if ":" not in line:
            continue
        lhs, rhs = line.split(":", 1)
        # The left side of ':' must end with a hex address like "0x200001b0".
        # This filters out lines like "xPSR: ..." where LHS is "xPSR".
        if not _ADDR_SUFFIX_RE.search(lhs):
            continue
        for token in rhs.split():
            raw = token[2:] if token.lower().startswith("0x") else token
            if token_re.fullmatch(raw):
                values.append(int(raw, 16))
    if len(values) < count:
        raise RuntimeError(f"cannot parse {count} values from memory output: {output}")
    return values[:count]
