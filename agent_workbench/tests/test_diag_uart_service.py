from __future__ import annotations

import shutil
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from agent_workbench.core import diag_uart_service


class _FakeSerial:
    next_reads: list[bytes] = []
    last_instance: "_FakeSerial | None" = None

    def __init__(self, port: str, baudrate: int, timeout: float):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._reads = list(type(self).next_reads)
        self.writes: list[bytes] = []
        type(self).last_instance = self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    @property
    def in_waiting(self) -> int:
        return len(self._reads[0]) if self._reads else 0

    def read(self, size: int = 1) -> bytes:
        if not self._reads:
            return b""
        chunk = self._reads[0]
        if size <= 0 or size >= len(chunk):
            return self._reads.pop(0)
        self._reads[0] = chunk[size:]
        return chunk[:size]

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def flush(self) -> None:
        return None

    def reset_input_buffer(self) -> None:
        return None

    def reset_output_buffer(self) -> None:
        return None


class DiagUartServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_diag_", dir=temp_root))
        self.cfg = {
            "diag_uart": {
                "enabled": True,
                "port": "COM5",
                "baudrate": 115200,
                "default_crc": "modbus",
                "response_timeout_sec": 0.05,
                "silence_timeout_sec": 0.01,
                "read_timeout_sec": 0.01,
            },
            "outputs": {
                "runtime_root_path": self.temp_dir,
            },
            "project_root_path": self.temp_dir,
        }
        self.serial_patch = mock.patch.object(
            diag_uart_service,
            "serial",
            types.SimpleNamespace(Serial=_FakeSerial),
        )
        self.serial_patch.start()

    def tearDown(self) -> None:
        self.serial_patch.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_hex_bytes_accepts_prefixed_tokens(self) -> None:
        self.assertEqual(
            diag_uart_service.parse_hex_bytes("0x01 0x03 0x00 0x10"),
            b"\x01\x03\x00\x10",
        )

    def test_execute_diag_exchange_appends_modbus_crc_and_captures_response(self) -> None:
        _FakeSerial.next_reads = [b"\x01\x06\x00\x10\x00\x01\x49\xCF"]

        result = diag_uart_service.execute_diag_exchange(
            self.cfg,
            "01 06 00 10 00 01",
            self.temp_dir / "diag_exchange.log",
        )

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.response_hex, "01 06 00 10 00 01 49 CF")
        self.assertEqual(
            _FakeSerial.last_instance.writes[0],
            diag_uart_service.append_modbus_crc(b"\x01\x06\x00\x10\x00\x01"),
        )
        log_text = (self.temp_dir / "diag_exchange.log").read_text(encoding="utf-8")
        self.assertIn("> 01 06 00 10 00 01 49 CF", log_text)
        self.assertIn("< 01 06 00 10 00 01 49 CF", log_text)
