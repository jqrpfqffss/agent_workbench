from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_workbench.core import openocd_service


class OpenOcdServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_openocd_", dir=temp_root))
        self.cfg = {
            "project_root_path": self.temp_dir,
            "template_values": {},
            "outputs": {"runtime_root_path": self.temp_dir},
            "tools": {
                "openocd": {
                    "daemon_cmd": "openocd -f interface/stlink.cfg -f target/stm32f1x.cfg",
                    "host": "127.0.0.1",
                    "telnet_port": 4444,
                    "startup_wait_sec": 0.01,
                }
            },
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_start_openocd_reports_started_when_telnet_is_ready_even_if_helper_pid_exits(self) -> None:
        with mock.patch.object(openocd_service, "command_exists", return_value=True), mock.patch.object(
            openocd_service, "spawn_detached_command_with_stdin_keeper", return_value=4321
        ), mock.patch.object(openocd_service, "_wait_ready", return_value=True), mock.patch.object(
            openocd_service, "is_process_alive", return_value=False
        ):
            message = openocd_service.start_openocd_daemon(self.cfg)

        self.assertIn("openocd started pid=4321", message)

    def test_start_openocd_still_times_out_when_telnet_is_not_ready_and_pid_is_gone(self) -> None:
        with mock.patch.object(openocd_service, "command_exists", return_value=True), mock.patch.object(
            openocd_service, "spawn_detached_command_with_stdin_keeper", return_value=4321
        ), mock.patch.object(openocd_service, "_wait_ready", return_value=False), mock.patch.object(
            openocd_service, "is_process_alive", return_value=False
        ):
            message = openocd_service.start_openocd_daemon(self.cfg)

        self.assertIn("startup timeout", message)

    def test_start_openocd_times_out_and_terminates_when_telnet_never_becomes_ready(self) -> None:
        with mock.patch.object(openocd_service, "command_exists", return_value=True), mock.patch.object(
            openocd_service, "spawn_detached_command_with_stdin_keeper", return_value=4321
        ), mock.patch.object(openocd_service, "_wait_ready", return_value=False), mock.patch.object(
            openocd_service, "is_process_alive", return_value=True
        ), mock.patch.object(openocd_service, "terminate_process") as terminate:
            message = openocd_service.start_openocd_daemon(self.cfg)

        self.assertIn("startup timeout", message)
        terminate.assert_called_once_with(4321)


if __name__ == "__main__":
    unittest.main()
