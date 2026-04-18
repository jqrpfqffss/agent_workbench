from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workbench import _normalize_argv


class WorkbenchCliTests(unittest.TestCase):
    def test_uart_exec_alias_with_inline_command_is_normalized(self) -> None:
        self.assertEqual(
            _normalize_argv(["uart", "--exec", "red on"]),
            ["uart", "exec", "--command", "red on"],
        )

    def test_uart_status_alias_is_normalized(self) -> None:
        self.assertEqual(
            _normalize_argv(["uart", "--status"]),
            ["uart", "status"],
        )

    def test_uart_command_payload_defaults_to_exec_even_with_start_alias(self) -> None:
        self.assertEqual(
            _normalize_argv(["uart", "--start", "--command", "red on"]),
            ["uart", "exec", "--command", "red on"],
        )
