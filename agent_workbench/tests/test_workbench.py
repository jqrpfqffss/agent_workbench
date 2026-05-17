from __future__ import annotations

import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import workbench  # type: ignore  # noqa: E402


class WorkbenchMonitorTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_workbench_", dir=temp_root))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_removed_commands_are_not_registered(self) -> None:
        parser = workbench.build_parser()
        commands = parser._subparsers._group_actions[0].choices

        self.assertNotIn("scan-project", commands)
        self.assertNotIn("context", commands)
        self.assertNotIn("test", commands)
        self.assertNotIn("verify", commands)
        self.assertNotIn("report", commands)
        self.assertNotIn("compare", commands)
        self.assertNotIn("session", commands)

    def test_monitor_only_exposes_kept_actions(self) -> None:
        parser = workbench.build_parser()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["monitor", "probe"])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["monitor", "run", "--out-dir", str(self.temp_dir)])
        parsed = parser.parse_args(["monitor", "stats"])
        self.assertEqual(parsed.action, "stats")

    def test_hidden_monitor_run_internal_accepts_out_dir(self) -> None:
        parser = workbench.build_parser()
        parsed = parser.parse_args(["__monitor-run", "--out-dir", str(self.temp_dir)])
        self.assertEqual(parsed.command, "__monitor-run")
        self.assertEqual(parsed.out_dir, str(self.temp_dir))


if __name__ == "__main__":
    unittest.main()
