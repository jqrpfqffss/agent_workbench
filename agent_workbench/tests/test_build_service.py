from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core import build_service


class BuildServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_build_service_", dir=temp_root))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_build_clears_previous_log_before_appending(self) -> None:
        log_path = self.temp_dir / "build.log"
        log_path.write_text("stale error\n", encoding="utf-8")
        calls: list[str] = []

        def fake_run_command(command: str, cwd: Path, log_path: Path) -> int:
            calls.append(command)
            with log_path.open("a", encoding="utf-8") as fp:
                fp.write(f"{command}\n")
            return 0

        old_run_command = build_service.run_command
        build_service.run_command = fake_run_command
        try:
            cfg = {
                "project_root_path": self.temp_dir,
                "project": {"build_dir_path": self.temp_dir / "build"},
                "tools": {
                    "cmake": {
                        "generator": "",
                        "build_type": "Debug",
                        "toolchain_file_path": str(self.temp_dir / "toolchain.cmake"),
                        "configure_args": [],
                        "build_args": [],
                    }
                },
                "template_values": {},
            }
            code = build_service.run_build(cfg, log_path)
        finally:
            build_service.run_command = old_run_command

        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("stale error", log_path.read_text(encoding="utf-8"))
