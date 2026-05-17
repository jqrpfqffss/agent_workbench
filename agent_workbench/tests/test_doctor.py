from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_workbench.core.doctor import run_doctor


class DoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_doctor_", dir=temp_root))
        self.runtime_root = self.temp_dir / "runtime"
        self.evidence_root = self.temp_dir / "evidence"
        self.generated_root = self.temp_dir / "generated"
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        self.generated_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _base_cfg(self, *, artifact: Path | None = None, monitor_symbol: Path | None = None) -> dict:
        toolchain_path = self.temp_dir / "toolchain.cmake"
        toolchain_path.write_text("# toolchain\n", encoding="utf-8")
        artifact_path = artifact or self.temp_dir / "missing.elf"
        monitor_symbol_path = monitor_symbol or artifact_path
        return {
            "project_root_path": self.temp_dir,
            "project": {
                "name": "demo",
                "artifact_file_path": artifact_path,
                "artifact_elf_path": artifact_path,
                "compile_commands_path": self.temp_dir / "missing.json",
            },
            "tools": {
                "cmake": {"toolchain_file_path": str(toolchain_path)},
                "openocd": {
                    "daemon_cmd": "openocd",
                    "config_files": ["interface/stlink.cfg", "target/stm32h7x.cfg"],
                },
                "flash": {"default_method": "openocd_cmd", "methods": {"openocd_cmd": {"flash": "openocd"}}},
                "symbols_nm": "arm-none-eabi-nm",
            },
            "outputs": {
                "runtime_root_path": self.runtime_root,
                "evidence_root_path": self.evidence_root,
                "generated_root_path": self.generated_root,
            },
            "hardware": {"mode": "prefer"},
            "template_values": {},
            "uart": {
                "enabled": True,
                "port": "COM3",
                "baudrate": 115200,
                "line_timeout_sec": 0.2,
                "ready_banner": "ready",
                "prompt": "cli>",
                "probe_commands": ["help"],
            },
            "diag_uart": {
                "enabled": True,
                "port": "COM99",
                "baudrate": 115200,
                "encoding": "utf-8",
                "read_timeout_sec": 0.05,
                "default_hex_requests": ["68 65 6C 70 0D 0A"],
            },
            "monitor": {
                "enabled": True,
                "items": [{"name": "g_data", "source": "symbol", "symbol": "g_data", "value_type": "u32"}],
                "symbols": {
                    "path": str(monitor_symbol_path),
                    "elf_path": str(monitor_symbol_path),
                },
                "openocd": {"connect_commands": []},
            },
        }

    def test_doctor_reports_core_runtime_status(self) -> None:
        cfg = self._base_cfg()

        with patch("agent_workbench.core.doctor._probe_serial_port_with_powershell", return_value=(True, "COM test")):
            code, summary = run_doctor(cfg, self.runtime_root)

        self.assertEqual(code, 0, summary)
        names = {item["name"]: item for item in summary["results"]}
        self.assertIn("diag_uart_backend", names)
        self.assertIn("diag_uart_port", names)
        self.assertIn("diag_uart_requests", names)
        self.assertIn("artifact_file", names)
        self.assertIn("monitor_symbol_image", names)
        self.assertIn("monitor_target_selection", names)
        self.assertIn("uart_port", names)
        self.assertIn("uart_markers", names)
        self.assertEqual(names["monitor_target_selection"]["level"], "warn")
        self.assertEqual(summary["fail_count"], 0)

    def test_doctor_accepts_axf_symbol_image_when_nm_can_parse_it(self) -> None:
        sample_elf = Path(__file__).resolve().parents[2] / "build" / "cmake-debug" / "serial.elf"
        if not sample_elf.exists():
            self.skipTest("serial.elf sample not available")
        sample_axf = self.temp_dir / "demo.axf"
        shutil.copyfile(sample_elf, sample_axf)
        cfg = self._base_cfg(artifact=sample_axf, monitor_symbol=sample_axf)
        cfg["uart"] = {"enabled": False, "probe_commands": []}
        cfg["diag_uart"] = {"enabled": False}
        cfg["monitor"]["openocd"] = {"connect_commands": ["targets stm32h7x.cpu0"]}

        code, summary = run_doctor(cfg, self.runtime_root)

        self.assertEqual(code, 0, summary)
        names = {item["name"]: item for item in summary["results"]}
        self.assertEqual(names["artifact_symbols"]["level"], "ok")
        self.assertEqual(names["monitor_symbol_image"]["level"], "ok")


if __name__ == "__main__":
    unittest.main()
