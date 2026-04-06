from __future__ import annotations

import re
import socket
from dataclasses import dataclass


PROMPT = b"> "


@dataclass
class OpenOcdConfig:
    host: str = "127.0.0.1"
    port: int = 4444
    timeout_sec: float = 2.0


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

    def command(self, cmd: str) -> str:
        if self.sock is None:
            raise RuntimeError("openocd socket not connected")
        self.sock.sendall((cmd.strip() + "\n").encode())
        return self._read_until_prompt()

    def halt(self) -> str:
        return self.command("halt")

    def resume(self) -> str:
        return self.command("resume")

    def read_register(self, register_name: str) -> int:
        output = self.command(f"reg {register_name}")
        match = re.search(r"0x([0-9a-fA-F]+)", output)
        if not match:
            raise RuntimeError(f"cannot parse register output: {output}")
        return int(match.group(1), 16)

    def read_mem_word(self, address: int) -> int:
        return self.read_mem_words(address, 1)[0]

    def read_mem_words(self, address: int, count: int) -> list[int]:
        output = self.command(f"mdw 0x{address:08x} {count}")
        words: list[int] = []
        for line in output.splitlines():
            if ":" not in line:
                continue
            rhs = line.split(":", 1)[1]
            for token in rhs.split():
                raw = token[2:] if token.lower().startswith("0x") else token
                if re.fullmatch(r"[0-9a-fA-F]{1,8}", raw):
                    words.append(int(raw, 16))
        if len(words) < count:
            raise RuntimeError(f"cannot parse {count} words from memory output: {output}")
        return words[:count]
