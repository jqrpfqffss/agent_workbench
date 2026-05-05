from __future__ import annotations

import json
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

    def __init__(self, port: str, baudrate: int, timeout: float, **kwargs):
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
                "port": "COM3",
                "baudrate": 115200,
                "data_bits": 8,
                "stop_bits": 1,
                "parity": "none",
                "encoding": "utf-8",
                "startup_drain_sec": 0.0,
                "read_timeout_sec": 0.01,
                "response_timeout_sec": 0.05,
                "response_idle_timeout_sec": 0.02,
                "default_hex_requests": ["68 65 6C 70 0D 0A"],
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

    def test_parse_hex_request_accepts_spaced_and_compact_hex(self) -> None:
        spaced = diag_uart_service.parse_hex_request("68 65 6C 70 0D 0A")
        compact = diag_uart_service.parse_hex_request("68656C700D0A")

        self.assertEqual(spaced.data, b"help\r\n")
        self.assertEqual(compact.data, b"help\r\n")
        self.assertEqual(spaced.hex_text, "68 65 6C 70 0D 0A")

    def test_parse_hex_request_rejects_invalid_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "even number"):
            diag_uart_service.parse_hex_request("123")
        with self.assertRaisesRegex(ValueError, "non-hex"):
            diag_uart_service.parse_hex_request("GG")

    def test_execute_diag_requests_writes_log_and_result(self) -> None:
        _FakeSerial.next_reads = [
            b"Available commands:\r\n",
            b"cli> ",
        ]
        log_path = self.temp_dir / "diag_exchange.log"
        result_path = self.temp_dir / "diag_exec_result.json"

        result = diag_uart_service.execute_diag_requests(
            self.cfg,
            ["68 65 6C 70 0D 0A"],
            log_path,
            result_path,
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn(b"help\r\n", _FakeSerial.last_instance.writes)
        self.assertTrue(log_path.exists())
        self.assertTrue(result_path.exists())
        log_text = log_path.read_text(encoding="utf-8")
        self.assertIn("hex=68 65 6C 70 0D 0A", log_text)
        self.assertIn("Available commands:", log_text)
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["exchange_count"], 1)
        self.assertEqual(payload["exchanges"][0]["response_size"], len(b"Available commands:\r\ncli> "))

    def test_execute_diag_requests_powershell_backend_error_returns_result(self) -> None:
        self.serial_patch.stop()
        log_path = self.temp_dir / "diag_exchange.log"
        result_path = self.temp_dir / "diag_exec_result.json"

        with mock.patch.object(diag_uart_service, "_powershell_available", return_value=True), mock.patch.object(
            diag_uart_service,
            "_powershell_exec_backend",
            side_effect=RuntimeError("The port 'COM3' does not exist."),
        ):
            result = diag_uart_service.execute_diag_requests(
                self.cfg,
                ["68 65 6C 70 0D 0A"],
                log_path,
                result_path,
            )

        self.assertEqual(result.exit_code, diag_uart_service.DIAG_EXIT_BACKEND_ERROR)
        self.assertTrue(log_path.exists())
        self.assertTrue(result_path.exists())
        self.assertIn("backend-error", log_path.read_text(encoding="utf-8"))
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "error")
        self.assertIn("COM3", payload["error"])
        self.serial_patch.start()
