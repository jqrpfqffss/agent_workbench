from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.config import load_config


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_config_", dir=temp_root))
        self.workbench_root = self.temp_dir / "agent_workbench"
        self.project_root = self.temp_dir / "demo_project"
        self.workbench_root.mkdir(parents=True, exist_ok=True)
        self.project_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_config_prefers_artifact_file_and_derives_openocd_commands(self) -> None:
        config_path = self.workbench_root / "agent_workbench.yaml"
        config_path.write_text(
            "project:\n"
            "  name: demo\n"
            "  root: ../demo_project\n"
            "  build_dir: build\n"
            "  artifact_file: build/demo.axf\n"
            "  artifact_elf: build/legacy_should_not_win.elf\n"
            "  compile_commands: build/compile_commands.json\n"
            "tools:\n"
            "  cmake:\n"
            "    toolchain_file: cmake/toolchain.cmake\n"
            "  openocd:\n"
            "    telnet_port: 5555\n"
            "    config_files:\n"
            "      - interface/stlink.cfg\n"
            "      - target/stm32h7x.cfg\n"
            "    extra_commands:\n"
            "      - adapter speed 4000\n"
            "monitor:\n"
            "  openocd:\n"
            "    connect_commands:\n"
            "      - targets stm32h7x.cpu0\n"
            "  symbols:\n"
            "    path: build/monitor.axf\n",
            encoding="utf-8",
        )

        cfg = load_config(config_path)

        self.assertTrue(str(cfg["project"]["artifact_file_path"]).endswith("demo.axf"))
        self.assertEqual(cfg["project"]["artifact_file_path"], cfg["project"]["artifact_elf_path"])
        self.assertEqual(cfg["template_values"]["artifact_file"], cfg["template_values"]["artifact_elf"])
        self.assertIn("target/stm32h7x.cfg", cfg["tools"]["openocd"]["daemon_cmd"])
        self.assertIn("telnet_port 5555", cfg["tools"]["openocd"]["daemon_cmd"])
        self.assertIn("program {artifact_file_posix} verify reset exit", cfg["tools"]["flash"]["methods"]["openocd_cmd"]["flash"])
        self.assertEqual(cfg["monitor"]["openocd"]["connect_commands"], ["targets stm32h7x.cpu0"])
        self.assertTrue(str(cfg["monitor"]["symbols"]["path"]).endswith("monitor.axf"))

    def test_load_config_falls_back_to_legacy_elf_keys(self) -> None:
        config_path = self.workbench_root / "agent_workbench.yaml"
        config_path.write_text(
            "project:\n"
            "  name: demo\n"
            "  root: ../demo_project\n"
            "  build_dir: build\n"
            "  artifact_elf: build/demo.elf\n"
            "  compile_commands: build/compile_commands.json\n"
            "monitor:\n"
            "  symbols:\n"
            "    elf_path: build/monitor.elf\n",
            encoding="utf-8",
        )

        cfg = load_config(config_path)

        self.assertTrue(str(cfg["project"]["artifact_file_path"]).endswith("demo.elf"))
        self.assertTrue(str(cfg["monitor"]["symbols"]["path"]).endswith("monitor.elf"))


if __name__ == "__main__":
    unittest.main()
