from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.reporting import derive_session_verdict


class ReportingTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_report_", dir=temp_root))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_manual_checks_turn_pass_into_needs_review(self) -> None:
        (self.temp_dir / "session_manifest.json").write_text(
            json.dumps(
                {
                    "mode": "feature",
                    "task": {
                        "id": "timer_led_blink",
                        "observability": {
                            "manual_checks": [
                                {
                                    "name": "red_led_blinks",
                                    "instructions": "Verify LED blinking on hardware.",
                                }
                            ]
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        (self.temp_dir / "events.jsonl").write_text(
            json.dumps({"event": "cli_probe_done", "code": 0, "saw_ready": True, "saw_prompt": True}) + "\n",
            encoding="utf-8",
        )
        (self.temp_dir / "assertions.jsonl").write_text(
            json.dumps({"status": "pass", "name": "cli_ready_banner_seen"}) + "\n",
            encoding="utf-8",
        )

        verdict = derive_session_verdict(self.temp_dir)

        self.assertEqual(verdict["status"], "needs_review")
        self.assertTrue(verdict["manual_checks_pending"])
        self.assertEqual(verdict["manual_checks"][0]["name"], "red_led_blinks")
