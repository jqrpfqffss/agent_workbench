from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.compare_service import compare_sessions, pick_latest_two_sessions


class CompareTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_compare_", dir=temp_root))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_compare_generates_report(self) -> None:
        old_dir = self.temp_dir / "debug_20260404_120000"
        new_dir = self.temp_dir / "debug_20260404_121000"
        old_dir.mkdir(parents=True)
        new_dir.mkdir(parents=True)
        (old_dir / "uart.log").write_text("ok\nwarn old\n", encoding="utf-8")
        (new_dir / "uart.log").write_text("ok\nwarn new\nextra\n", encoding="utf-8")
        (old_dir / "monitor_samples.csv").write_text("ts,item,value,ok,message\n1,temp,10,1,\n2,temp,11,1,\n", encoding="utf-8")
        (new_dir / "monitor_samples.csv").write_text("ts,item,value,ok,message\n1,temp,12,1,\n2,temp,13,1,\n", encoding="utf-8")

        report = compare_sessions(old_dir, new_dir, new_dir / "compare_vs_old.md")

        self.assertTrue(report.exists())
        text = report.read_text(encoding="utf-8")
        self.assertIn("Session Compare Report", text)
        self.assertIn("warn_like", text)
        self.assertIn("temp", text)

    def test_pick_latest_two_sessions(self) -> None:
        (self.temp_dir / "debug_20260404_120000").mkdir()
        (self.temp_dir / "debug_20260404_121000").mkdir()
        old_dir, new_dir = pick_latest_two_sessions(self.temp_dir)
        self.assertEqual(old_dir.name, "debug_20260404_120000")
        self.assertEqual(new_dir.name, "debug_20260404_121000")
