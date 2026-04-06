from __future__ import annotations

import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


class CliCoreHostTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]
        self.cli_core_c = self.repo_root / "Core" / "App" / "cli" / "debug_cli_core.c"
        self.cli_core_include_dir = self.repo_root / "Core" / "App" / "cli"
        if not self.cli_core_c.exists():
            self.skipTest("project does not provide Core/App/cli/debug_cli_core.c; skipping SmartFarm-specific host harness")
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_cli_core_", dir=temp_root))
        self.stub_root = self.temp_dir / "stubs"
        (self.stub_root / "cli").mkdir(parents=True)
        (self.stub_root / "global").mkdir(parents=True)
        (self.stub_root / "pump").mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write(self, relative: str, content: str) -> None:
        path = self.stub_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _prepare_stub_headers(self) -> None:
        self._write(
            "cli/debug_cli.h",
            textwrap.dedent(
                """\
                #ifndef SMARTFARM_DEBUG_CLI_H
                #define SMARTFARM_DEBUG_CLI_H
                #include <stdint.h>
                typedef struct {
                  uint32_t rx_bytes;
                  uint32_t rx_lines;
                  uint32_t cmd_ok;
                  uint32_t cmd_err;
                  uint32_t rx_overflow;
                  uint32_t uart_error;
                  char last_cmd[32];
                } DebugCliStatsData;
                extern DebugCliStatsData DebugCliStats;
                #endif
                """
            ),
        )
        self._write(
            "global/farmState.h",
            textwrap.dedent(
                """\
                #ifndef SMARTFARM_FARM_STATE_H
                #define SMARTFARM_FARM_STATE_H
                #include <stdint.h>
                typedef struct {
                  float temperature;
                  float humidity;
                  uint16_t rainGauge;
                  uint16_t soilMoisture;
                  uint16_t lightIntensity;
                  uint8_t waterPumpState;
                  uint8_t pumpControlMode;
                } FarmState;
                typedef struct {
                  float minTemperature;
                  float maxTemperature;
                  float minHumidity;
                  float maxHumidity;
                  uint16_t maxRainGauge;
                  uint16_t minSoilMoisture;
                  uint16_t maxSoilMoisture;
                  uint16_t minLightIntensity;
                  uint16_t maxLightIntensity;
                } FarmSafeRange;
                extern FarmState farmState;
                extern FarmSafeRange farmSafeRange;
                #endif
                """
            ),
        )
        self._write(
            "pump/pump.h",
            textwrap.dedent(
                """\
                #ifndef SMARTFARM_PUMP_H
                #define SMARTFARM_PUMP_H
                void Pump_On(void);
                void Pump_Off(void);
                #endif
                """
            ),
        )
        self._write(
            "BeepTimer.h",
            textwrap.dedent(
                """\
                #ifndef SMARTFARM_BEEP_TIMER_H
                #define SMARTFARM_BEEP_TIMER_H
                void Beep_on(void);
                void Beep_off(void);
                #endif
                """
            ),
        )
        self._write(
            "cmsis_os2.h",
            textwrap.dedent(
                """\
                #ifndef CMSIS_OS2_H
                #define CMSIS_OS2_H
                #include <stdint.h>
                #define __disable_irq() ((void)0)
                #define __enable_irq() ((void)0)
                uint32_t osKernelGetTickCount(void);
                #endif
                """
            ),
        )
        self._write(
            "utils.h",
            textwrap.dedent(
                """\
                #ifndef SMARTFARM_UTILS_H
                #define SMARTFARM_UTILS_H
                void floatToIntDec(float value, int *intPart, int *decPart);
                #endif
                """
            ),
        )

    def _prepare_harness(self) -> Path:
        harness = self.temp_dir / "cli_core_harness.c"
        harness.write_text(
            textwrap.dedent(
                """\
                #include <math.h>
                #include <stdint.h>
                #include <stdio.h>
                #include <stdlib.h>
                #include <string.h>

                #include "cli/debug_cli.h"
                #include "cli/debug_cli_core.h"
                #include "global/farmState.h"

                DebugCliStatsData DebugCliStats;
                FarmState farmState = {26.3f, 55.4f, 2, 48, 650, 0, 0};
                FarmSafeRange farmSafeRange = {18.0f, 32.0f, 30.0f, 80.0f, 10, 30, 80, 200, 900};

                static char g_output[8192];
                static size_t g_output_len = 0U;
                static uint32_t g_tick = 1234U;

                static void reset_output(void) {
                  memset(g_output, 0, sizeof(g_output));
                  g_output_len = 0U;
                }

                static void print_block(const char *label) {
                  printf("=== %s ===\\n%s=== END %s ===\\n", label, g_output, label);
                }

                void DebugCliCore_WriteLine(const char *text) {
                  int written = snprintf(g_output + g_output_len, sizeof(g_output) - g_output_len, "%s\\n", text ? text : "");
                  if (written > 0) {
                    g_output_len += (size_t)written;
                  }
                }

                void Pump_On(void) {
                  farmState.waterPumpState = 1U;
                }

                void Pump_Off(void) {
                  farmState.waterPumpState = 0U;
                }

                void Beep_on(void) {
                  (void)0;
                }

                void Beep_off(void) {
                  (void)0;
                }

                uint32_t osKernelGetTickCount(void) {
                  return g_tick++;
                }

                void floatToIntDec(float value, int *intPart, int *decPart) {
                  float positive = value >= 0.0f ? value : -value;
                  int integer = (int)positive;
                  int decimal = (int)((positive - (float)integer) * 10.0f + 0.5f);
                  if (value < 0.0f) {
                    integer = -integer;
                  }
                  *intPart = integer;
                  *decPart = decimal;
                }

                static void run_command(const char *command) {
                  char line[128];
                  snprintf(line, sizeof(line), "%s", command);
                  reset_output();
                  DebugCliCore_ProcessLine(line);
                  print_block(command);
                }

                int main(void) {
                  reset_output();
                  DebugCliCore_Init();
                  print_block("BOOT");

                  DebugCliCore_ReportWarningFloat("temperature_high", 35.5f);
                  run_command("help");
                  run_command("version");
                  run_command("pump on");
                  run_command("pump auto");
                  run_command("set_range min_temp 18.5");
                  run_command("alerts");
                  run_command("stats");
                  run_command("selftest");
                  run_command("unknown");
                  reset_output();
                  DebugCliCore_ProcessOverflow();
                  print_block("OVERFLOW");
                  return 0;
                }
                """
            ),
            encoding="utf-8",
        )
        return harness

    def _build_harness(self) -> Path:
        self._prepare_stub_headers()
        harness = self._prepare_harness()
        exe_path = self.temp_dir / "cli_core_harness.exe"
        cmd = [
            "gcc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            f"-I{self.stub_root}",
            f"-I{self.repo_root / 'Core' / 'App'}",
            f"-I{self.cli_core_include_dir}",
            '-DSMARTFARM_FW_VERSION="1.2.3"',
            '-DSMARTFARM_BUILD_PROFILE="host-test"',
            str(self.cli_core_c),
            str(harness),
            "-o",
            str(exe_path),
        ]
        subprocess.check_call(cmd, cwd=str(self.repo_root))
        return exe_path

    def test_cli_core_host_harness(self) -> None:
        exe_path = self._build_harness()
        proc = subprocess.run([str(exe_path)], cwd=str(self.repo_root), check=True, capture_output=True, text=True)
        stdout = proc.stdout
        self.assertIn("cli ready fw=1.2.3 profile=host-test", stdout)
        self.assertIn("cmd | usage | args", stdout)
        self.assertIn("version fw=1.2.3 profile=host-test", stdout)
        self.assertIn("OK pump on", stdout)
        self.assertIn("OK pump auto", stdout)
        self.assertIn("OK set_range key=min_temp value=18.5", stdout)
        self.assertIn("alerts count=", stdout)
        self.assertIn("stats rx_bytes=", stdout)
        self.assertIn("selftest status=", stdout)
        self.assertIn("ERR cmd", stdout)
        self.assertIn("ERR overflow", stdout)
