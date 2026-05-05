from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import workbench  # type: ignore  # noqa: E402


class _FakeMonitorEngine:
    def __init__(self, cfg: dict, out_dir: Path):
        self.cfg = cfg
        self.out_dir = out_dir

    def probe_once(self):
        return 0, {
            "symbol_image": "build/demo.axf",
            "connect_commands": ["targets stm32h7x.cpu0"],
            "items": [{"name": "g_data", "source": "symbol", "value": 1, "ok": True, "error": ""}],
        }


class WorkbenchMonitorTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_workbench_", dir=temp_root))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_monitor_probe_builds_structured_payload(self) -> None:
        args = argparse.Namespace(action="probe", config="unused", out_dir=str(self.temp_dir), source="", dest="", json=False)
        cfg = {"outputs": {"runtime_root_path": self.temp_dir}}

        with patch("workbench._cfg", return_value=cfg):
            with patch("core.monitor_service.MonitorEngine", _FakeMonitorEngine):
                with patch("workbench._emit", side_effect=lambda _args, payload, _lines: payload["exit_code"]) as emit:
                    code = workbench._cmd_monitor(args)

        self.assertEqual(code, 0)
        payload = emit.call_args.args[1]
        self.assertEqual(payload["command"], "monitor probe")
        self.assertEqual(payload["details"]["items"][0]["name"], "g_data")


if __name__ == "__main__":
    unittest.main()
