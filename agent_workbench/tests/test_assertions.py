from __future__ import annotations

import shutil
import tempfile
import unittest
from json import dumps
from pathlib import Path

from agent_workbench.core.assertions import evaluate_assertions


class AssertionTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_assert_", dir=temp_root))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_file_and_uart_assertions(self) -> None:
        (self.temp_dir / "uart.log").write_text("hello version\n", encoding="utf-8")
        (self.temp_dir / "cli_transcript.log").write_text(
            "[2026-04-05T00:00:00.000+00:00] < version fw=1.2.0\n"
            "[2026-04-05T00:00:00.100+00:00] < help | version\n",
            encoding="utf-8",
        )
        (self.temp_dir / "session_manifest.json").write_text("{}", encoding="utf-8")

        passed, failed, skipped = evaluate_assertions(
            self.temp_dir,
            [
                {"name": "manifest", "type": "file_exists", "path": "session_manifest.json"},
                {"name": "uart", "type": "uart_contains", "needle": "version"},
                {"name": "cli", "type": "cli_contains", "needle": "fw=1.2.0"},
            ],
        )

        self.assertEqual(passed, 3)
        self.assertEqual(failed, 0)
        self.assertEqual(skipped, 0)

    def test_cli_protocol_assertions(self) -> None:
        (self.temp_dir / "cli_transcript.log").write_text(
            "[2026-04-05T00:00:00.000+00:00] < cli ready fw=1.2.0 profile=debug\n"
            "[2026-04-05T00:00:00.100+00:00] < cli>\n"
            "[2026-04-05T00:00:00.200+00:00] < pong\n"
            "[2026-04-05T00:00:00.300+00:00] < cli>\n",
            encoding="utf-8",
        )
        (self.temp_dir / "cli_diag.json").write_text(
            dumps({"stats": {"rx_bytes": 12, "cmd_ok": 2}, "classification": {"code": "ok"}}),
            encoding="utf-8",
        )

        passed, failed, skipped = evaluate_assertions(
            self.temp_dir,
            [
                {"name": "ready", "type": "cli_ready"},
                {"name": "prompt", "type": "cli_prompt_seen"},
                {"name": "timeout", "type": "cli_no_timeout"},
                {"name": "diag", "type": "cli_diag_field_between", "field": "stats.rx_bytes", "min": 1, "max": 100},
            ],
        )

        self.assertEqual(passed, 4)
        self.assertEqual(failed, 0)
        self.assertEqual(skipped, 0)
