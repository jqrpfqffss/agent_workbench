from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from agent_workbench.core.build_errors import parse_build_log


class BuildErrorsTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_build_errors_", dir=temp_root))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_build_log_extracts_structured_fix_for_undeclared_timer_handle(self) -> None:
        source_path = self.temp_dir / "Core" / "Src" / "main.c"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(
            "int main(void) {\n"
            "  htim999.Instance = TIM1;\n"
            "  return 0;\n"
            "}\n",
            encoding="utf-8",
        )
        log_path = self.temp_dir / "build.log"
        log_path.write_text(
            "Core/Src/main.c:2:3: error: 'htim999' undeclared (first use in this function)\n",
            encoding="utf-8",
        )

        parsed = parse_build_log(log_path, self.temp_dir)

        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].error_code, "undeclared_identifier")
        self.assertEqual(parsed[0].category, "undefined")
        self.assertTrue(parsed[0].context_lines)
        self.assertEqual(parsed[0].suggested_fix["action_type"], "add_declaration")
        self.assertEqual(parsed[0].suggested_fix["target_files"], ["Core/Inc/main.h"])
        self.assertEqual(parsed[0].suggested_fix["code"], "extern TIM_HandleTypeDef htim999;")

    def test_parse_build_log_extracts_structured_fix_for_unknown_type(self) -> None:
        source_path = self.temp_dir / "Core" / "Src" / "main.c"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("TIM_HandleTypeDef h;\n", encoding="utf-8")
        log_path = self.temp_dir / "build.log"
        log_path.write_text(
            "Core/Src/main.c:1:1: error: unknown type name 'TIM_HandleTypeDef'\n",
            encoding="utf-8",
        )

        parsed = parse_build_log(log_path, self.temp_dir)

        self.assertEqual(parsed[0].error_code, "unknown_type_name")
        self.assertEqual(parsed[0].category, "type")
        self.assertEqual(parsed[0].suggested_fix["action_type"], "add_include")
        self.assertIn("stm32f1xx_hal.h", parsed[0].suggested_fix["code"])
