from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import shutil

from agent_workbench.core.flash_service import run_flash, run_reset


class FlashServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_flash_"))
        self.cfg = {
            "project_root_path": self.temp_dir,
            "template_values": {"artifact_elf": "firmware.elf"},
            "tools": {
                "flash": {
                    "default_method": "openocd_cmd",
                    "methods": {
                        "openocd_cmd": {
                            "flash": "openocd program {artifact_elf}",
                            "reset": "openocd reset",
                        }
                    },
                }
            },
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_flash_stops_managed_openocd_before_exclusive_command(self) -> None:
        with patch("agent_workbench.core.flash_service.stop_openocd_daemon") as stop_openocd:
            with patch("agent_workbench.core.flash_service.run_command", return_value=0) as run_command:
                code = run_flash(self.cfg, None, self.temp_dir / "flash.log")

        self.assertEqual(code, 0)
        stop_openocd.assert_called_once_with(self.cfg)
        self.assertEqual(run_command.call_args.args[0], "openocd program firmware.elf")

    def test_reset_stops_managed_openocd_before_exclusive_command(self) -> None:
        with patch("agent_workbench.core.flash_service.stop_openocd_daemon") as stop_openocd:
            with patch("agent_workbench.core.flash_service.run_command", return_value=0) as run_command:
                code = run_reset(self.cfg, None, self.temp_dir / "reset.log")

        self.assertEqual(code, 0)
        stop_openocd.assert_called_once_with(self.cfg)
        self.assertEqual(run_command.call_args.args[0], "openocd reset")


if __name__ == "__main__":
    unittest.main()
