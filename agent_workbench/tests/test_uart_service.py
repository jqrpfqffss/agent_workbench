from __future__ import annotations

import json
import shutil
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from agent_workbench.core import uart_service


class _FakeSerial:
    next_reads: list[bytes] = []
    write_hooks: dict[bytes, list[bytes]] = {}
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

    def readline(self) -> bytes:
        return self._reads.pop(0) if self._reads else b""

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
        extra = type(self).write_hooks.get(data)
        if extra:
            self._reads.extend(extra)
        return len(data)

    def flush(self) -> None:
        return None

    def reset_input_buffer(self) -> None:
        return None

    def reset_output_buffer(self) -> None:
        return None


class UartExecTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_uart_", dir=temp_root))
        _FakeSerial.write_hooks = {}
        self.cfg = {
            "uart": {
                "enabled": True,
                "port": "COM3",
                "baudrate": 9600,
                "encoding": "utf-8",
                "line_timeout_sec": 0.01,
                "startup_drain_sec": 0.0,
                "ready_banner": "cli ready",
                "prompt": "cli>",
                "ready_timeout_sec": 0.05,
                "command_timeout_sec": 0.05,
                "exec_require_ready": True,
                "exec_fail_on_timeout": True,
            },
            "outputs": {
                "runtime_root_path": self.temp_dir,
            },
            "project_root_path": self.temp_dir,
            "tools": {
                "flash": {
                    "default_method": "openocd_cmd",
                    "methods": {
                        "openocd_cmd": {"reset": "openocd -c reset"},
                    },
                },
                "openocd": {
                    "daemon_cmd": "openocd",
                    "host": "127.0.0.1",
                    "telnet_port": 4444,
                    "startup_wait_sec": 0.1,
                },
            },
            "template_values": {},
        }
        self.serial_patch = mock.patch.object(
            uart_service,
            "serial",
            types.SimpleNamespace(Serial=_FakeSerial),
        )
        self.serial_patch.start()

    def tearDown(self) -> None:
        self.serial_patch.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_uart_exec_waits_for_ready_and_prompt(self) -> None:
        _FakeSerial.next_reads = [
            b"cli ready fw=1.2.3 profile=debug\r\n",
            b"cli> ",
            b"pong\r\n",
            b"cli> ",
        ]
        with mock.patch.object(uart_service, "run_reset", return_value=0) as run_reset_mock:
            result = uart_service.execute_uart_commands(
                self.cfg,
                ["ping"],
                self.temp_dir / "cli_transcript.log",
                reset_first=True,
                expect_ready=True,
            )

        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.saw_ready)
        self.assertTrue(result.saw_prompt)
        self.assertEqual(result.timeout_commands, [])
        self.assertEqual(run_reset_mock.call_count, 1)
        self.assertIn(b"ping\r\n", _FakeSerial.last_instance.writes)
        transcript = (self.temp_dir / "cli_transcript.log").read_text(encoding="utf-8")
        self.assertIn("cli ready", transcript)
        self.assertIn("pong", transcript)
        self.assertIn("cli>", transcript)

    def test_uart_exec_handles_prompt_without_newline(self) -> None:
        self.cfg["uart"]["ready_banner"] = "STM32 UART CLI ready."
        _FakeSerial.next_reads = [
            b"STM32 UART CLI ready.\r\nConsole: USART2 @ 115200 8N1\r\nType 'help' to list commands.\r\n\r\ncli> ",
            b"help\r\nAvailable commands:\r\n",
            b"cli> ",
        ]

        with mock.patch.object(uart_service, "run_reset", return_value=0):
            result = uart_service.execute_uart_commands(
                self.cfg,
                ["help"],
                self.temp_dir / "cli_transcript.log",
                reset_first=True,
                expect_ready=True,
            )

        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.saw_ready)
        self.assertTrue(result.saw_prompt)
        transcript = (self.temp_dir / "cli_transcript.log").read_text(encoding="utf-8")
        self.assertIn("STM32 UART CLI ready.", transcript)
        self.assertIn("Available commands:", transcript)
        self.assertIn("cli>", transcript)

    def test_uart_exec_recovers_running_cli_without_reset_banner(self) -> None:
        _FakeSerial.next_reads = []
        _FakeSerial.write_hooks = {
            b"\r\n": [b"cli> "],
            b"help\r\n": [b"Available commands:\r\n", b"cli> "],
        }

        result = uart_service.execute_uart_commands(
            self.cfg,
            ["help"],
            self.temp_dir / "cli_transcript.log",
            reset_first=False,
            expect_ready=True,
        )

        self.assertEqual(result.exit_code, 0)
        self.assertFalse(result.saw_ready)
        self.assertTrue(result.saw_prompt)
        self.assertEqual(_FakeSerial.last_instance.writes[:2], [b"\r\n", b"help\r\n"])
        transcript = (self.temp_dir / "cli_transcript.log").read_text(encoding="utf-8")
        self.assertIn("prompt-sync send-empty-line", transcript)
        self.assertIn("prompt-sync acquired", transcript)
        self.assertIn("Available commands:", transcript)

    def test_uart_exec_timeout_generates_diag(self) -> None:
        _FakeSerial.next_reads = [
            b"cli ready fw=1.2.3 profile=debug\r\n",
            b"cli> ",
        ]
        diag_path = self.temp_dir / "cli_diag.json"

        def _fake_diag(*args, **kwargs):
            diag_path.write_text(
                json.dumps(
                    {
                        "status": "ok",
                        "stats": {"rx_bytes": 0, "cmd_ok": 0},
                        "classification": {"code": "rx_zero", "summary": "rx zero", "detail": "check wiring"},
                    }
                ),
                encoding="utf-8",
            )
            return diag_path

        with mock.patch.object(uart_service, "collect_cli_diag", side_effect=_fake_diag):
            result = uart_service.execute_uart_commands(
                self.cfg,
                ["help"],
                self.temp_dir / "cli_transcript.log",
                expect_ready=True,
            )

        self.assertEqual(result.exit_code, 33)
        self.assertEqual(result.timeout_commands, ["help"])
        self.assertEqual(result.diag_path, diag_path)
        self.assertEqual(result.diag["classification"]["code"], "rx_zero")
        transcript = (self.temp_dir / "cli_transcript.log").read_text(encoding="utf-8")
        self.assertIn("[timeout]", transcript)

    def test_uart_exec_reset_failure_returns_reset_diag(self) -> None:
        _FakeSerial.next_reads = []

        with mock.patch.object(uart_service, "run_reset", return_value=1):
            result = uart_service.execute_uart_commands(
                self.cfg,
                ["help"],
                self.temp_dir / "cli_transcript.log",
                reset_first=True,
                expect_ready=True,
            )

        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.reset_exit_code, 1)
        self.assertEqual(result.diag["classification"]["code"], "reset_failed")
        self.assertEqual(result.diag["reset_exit_code"], 1)
        transcript = (self.temp_dir / "cli_transcript.log").read_text(encoding="utf-8")
        self.assertIn("reset-first exit=1", transcript)

    def test_uart_exec_powershell_backend_error_returns_diag_instead_of_traceback(self) -> None:
        self.serial_patch.stop()
        diag_path = self.temp_dir / "cli_diag.json"

        def _fake_diag(*args, **kwargs):
            diag_path.write_text(
                json.dumps(
                    {
                        "status": "error",
                        "classification": {"code": "rx_zero", "summary": "rx zero", "detail": "port missing"},
                    }
                ),
                encoding="utf-8",
            )
            return diag_path

        with mock.patch.object(uart_service, "_powershell_available", return_value=True), mock.patch.object(
            uart_service,
            "_powershell_exec_backend",
            side_effect=RuntimeError("The port 'COM3' does not exist."),
        ), mock.patch.object(uart_service, "collect_cli_diag", side_effect=_fake_diag):
            result = uart_service.execute_uart_commands(
                self.cfg,
                ["help"],
                self.temp_dir / "cli_transcript.log",
                expect_ready=True,
            )

        self.assertEqual(result.exit_code, 35)
        self.assertEqual(result.diag_path, diag_path)
        self.assertEqual(result.diag["classification"]["code"], "rx_zero")
        transcript = (self.temp_dir / "cli_transcript.log").read_text(encoding="utf-8")
        self.assertIn("backend-error", transcript)
        self.serial_patch.start()

    def test_uart_exec_powershell_reset_failure_returns_reset_diag(self) -> None:
        self.serial_patch.stop()
        with mock.patch.object(uart_service, "_powershell_available", return_value=True), mock.patch.object(
            uart_service,
            "_powershell_exec_backend",
            return_value=uart_service.UartExecResult(
                exit_code=1,
                transcript_lines=[],
                saw_ready=False,
                saw_prompt=False,
                timeout_commands=[],
                reset_exit_code=1,
            ),
        ):
            result = uart_service.execute_uart_commands(
                self.cfg,
                ["help"],
                self.temp_dir / "cli_transcript.log",
                reset_first=True,
                expect_ready=True,
            )

        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.diag["classification"]["code"], "reset_failed")
        self.assertEqual(result.diag["reset_exit_code"], 1)
        self.serial_patch.start()
