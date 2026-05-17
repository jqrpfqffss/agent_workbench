from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_workbench.core.monitor_service import (
    MonitorEngine,
    _convert_value,
    _value_width_bits,
    export_monitor_wide,
    summarize_monitor_samples,
    stop_monitor_daemon,
)
from agent_workbench.core.openocd_client import _parse_memory_values


class FakeOpenOcd:
    def __init__(self) -> None:
        self.mem_calls: list[tuple[int, int]] = []
        self.register_calls: list[str] = []
        self.commands: list[str] = []
        self.connected = False

    def connect(self) -> None:
        self.connected = True

    def close(self) -> None:
        self.connected = False

    def run_commands(self, commands: list[str]) -> list[str]:
        self.commands.extend(commands)
        return [f"ok:{item}" for item in commands]

    def halt(self) -> str:
        self.commands.append("halt")
        return "halted"

    def resume(self) -> str:
        self.commands.append("resume")
        return "resumed"

    def read_mem_value(self, address: int, width_bits: int = 32) -> int:
        self.mem_calls.append((address, width_bits))
        return {8: 0xFE, 16: 0xFFFE, 32: 0xFFFFFFFE}[width_bits]

    def read_mem(self, address: int, count: int, width_bits: int = 32) -> list[int]:
        self.mem_calls.append((address, width_bits))
        return [{8: 0xFE, 16: 0xFFFE, 32: 0xFFFFFFFE}[width_bits] for _ in range(count)]

    def read_register(self, register_name: str) -> int:
        self.register_calls.append(register_name)
        return 0x12345678


class MonitorServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / "runtime" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="awb_monitor_", dir=temp_root))
        self.cfg = {
            "monitor": {
                "sample_hz": 10,
                "register_sample_hz": 10,
                "ring_size": 4,
                "export_interval_sec": 1,
                "flush_interval_sec": 0.01,
                "read_while_running": True,
                "halt_per_sample": False,
                "openocd": {
                    "host": "127.0.0.1",
                    "port": 4444,
                    "timeout_sec": 0.1,
                    "connect_commands": ["targets stm32h7x.cpu0"],
                },
                "symbols": {
                    "path": str(self.temp_dir / "missing.axf"),
                    "elf_path": str(self.temp_dir / "missing.axf"),
                },
                "items": [],
            },
            "tools": {"symbols_nm": "arm-none-eabi-nm"},
            "outputs": {"runtime_root_path": self.temp_dir},
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _engine(self) -> tuple[MonitorEngine, FakeOpenOcd]:
        engine = MonitorEngine(self.cfg, self.temp_dir)
        fake = FakeOpenOcd()
        engine.openocd = fake  # type: ignore[assignment]
        return engine, fake

    def test_memory_dump_parser_honors_width(self) -> None:
        self.assertEqual(_parse_memory_values("0x20000000: fe 01", 2, max_digits=2), [0xFE, 0x01])
        self.assertEqual(_parse_memory_values("0x20000000: fffe 0001", 2, max_digits=4), [0xFFFE, 0x0001])
        self.assertEqual(_parse_memory_values("0x20000000: 00000009", 1, max_digits=8), [9])

    def test_value_type_width_and_signed_conversion(self) -> None:
        self.assertEqual(_value_width_bits("u8"), 8)
        self.assertEqual(_value_width_bits("s16"), 16)
        self.assertEqual(_value_width_bits("float"), 32)
        self.assertEqual(_convert_value(0xFE, "s8"), -2)
        self.assertEqual(_convert_value(0xFFFE, "s16"), -2)
        self.assertAlmostEqual(_convert_value(0x41200000, "float"), 10.0)

    def test_read_item_supports_symbol_address_and_memory_mapped_registers(self) -> None:
        engine, fake = self._engine()
        engine.symbols = {"g_data": 0x200001B0}

        self.assertEqual(
            engine._read_item({"source": "symbol", "symbol": "g_data", "value_type": "u32"}),
            (0xFFFFFFFE, 0xFFFFFFFE),
        )
        self.assertEqual(fake.mem_calls[-1], (0x200001B0, 32))

        self.assertEqual(
            engine._read_item({"source": "address", "address": "0x200001b1", "value_type": "s8"}),
            (0xFE, -2),
        )
        self.assertEqual(fake.mem_calls[-1], (0x200001B1, 8))

        self.assertEqual(
            engine._read_item({"source": "register", "target": "0x4001080c", "value_type": "u16"}),
            (0xFFFE, 0xFFFE),
        )
        self.assertEqual(fake.mem_calls[-1], (0x4001080C, 16))

    def test_cpu_register_still_uses_openocd_reg_command(self) -> None:
        engine, fake = self._engine()

        self.assertEqual(
            engine._read_item({"source": "register", "target": "r0", "value_type": "u32"}),
            (0x12345678, 0x12345678),
        )
        self.assertEqual(fake.register_calls, ["r0"])

    def test_init_files_truncates_jsonl_and_records_resolved_items(self) -> None:
        engine, _fake = self._engine()
        engine.items = [{"name": "g_data", "source": "symbol", "symbol": "g_data", "value_type": "u32"}]
        engine.symbols = {"g_data": 0x200001B0}
        engine.paths.jsonl_path.write_text('{"stale": true}\n', encoding="utf-8")
        engine.paths.meta_path.write_text('{"stale": true}\n', encoding="utf-8")

        engine._init_files()

        self.assertEqual(engine.paths.jsonl_path.read_text(encoding="utf-8"), "")
        meta = [json.loads(line) for line in engine.paths.meta_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(meta[0]["event"], "monitor_start")
        self.assertEqual(meta[0]["items"][0]["resolved_address"], "0x200001b0")
        self.assertEqual(meta[0]["symbol_image"], str(self.temp_dir / "missing.axf"))
        self.assertEqual(
            engine.paths.wide_csv_path.read_text(encoding="utf-8").splitlines()[0],
            "sample_index,elapsed_ms,ts,g_data",
        )
        self.assertEqual(
            engine.paths.csv_path.read_text(encoding="utf-8").splitlines()[0],
            "sample_index,elapsed_ms,ts,item,value,ok,message",
        )

    def test_export_monitor_wide_pivots_long_samples_for_plotting(self) -> None:
        src = self.temp_dir / "monitor_samples.csv"
        dst = self.temp_dir / "monitor_samples_wide.csv"
        src.write_text(
            "sample_index,elapsed_ms,ts,item,value,ok,message\n"
            "0,0.125000,2026-05-05T03:21:48.729+00:00,g_data,11200,1,\n"
            "0,0.125000,2026-05-05T03:21:48.729+00:00,g_data1,2800.0,1,\n"
            "1,1.125000,2026-05-05T03:21:48.730+00:00,g_data,11202,1,\n"
            "1,1.125000,2026-05-05T03:21:48.730+00:00,g_data1,,0,read failed\n",
            encoding="utf-8",
        )

        message = export_monitor_wide(src, dst)

        self.assertIn("exported wide table", message)
        self.assertEqual(
            dst.read_text(encoding="utf-8").splitlines(),
            [
                "sample_index,elapsed_ms,ts,g_data,g_data1",
                "0,0.125000,2026-05-05T03:21:48.729+00:00,11200,2800.0",
                "1,1.125000,2026-05-05T03:21:48.730+00:00,11202,",
            ],
        )

    def test_summarize_monitor_samples_uses_unique_sample_index(self) -> None:
        src = self.temp_dir / "monitor_samples.csv"
        src.write_text(
            "sample_index,elapsed_ms,ts,item,value,ok,message\n"
            "0,0.000000,2026-05-05T03:21:48.729+00:00,g_data,1,1,\n"
            "0,0.000000,2026-05-05T03:21:48.729+00:00,g_data1,2,1,\n"
            "1,1.000000,2026-05-05T03:21:48.730+00:00,g_data,3,1,\n"
            "1,1.000000,2026-05-05T03:21:48.730+00:00,g_data1,4,1,\n"
            "2,2.000000,2026-05-05T03:21:48.731+00:00,g_data,5,1,\n",
            encoding="utf-8",
        )

        stats = summarize_monitor_samples(src)

        self.assertTrue(stats["ok"])
        self.assertEqual(stats["sample_count"], 3)
        self.assertEqual(stats["actual_sample_hz"], 1000.0)

    def test_summarize_monitor_samples_tolerates_nul_in_messages(self) -> None:
        src = self.temp_dir / "monitor_samples.csv"
        src.write_text(
            "sample_index,elapsed_ms,ts,item,value,ok,message\n"
            "0,0.000000,2026-05-05T03:21:48.729+00:00,g_data,,0,\x00read failed\n"
            "1,1.000000,2026-05-05T03:21:48.730+00:00,g_data,,0,read failed\n",
            encoding="utf-8",
        )

        stats = summarize_monitor_samples(src)

        self.assertTrue(stats["ok"])
        self.assertEqual(stats["sample_count"], 2)
        self.assertEqual(stats["actual_sample_hz"], 1000.0)

    def test_stop_monitor_also_stops_managed_openocd_without_monitor_pid(self) -> None:
        with patch("agent_workbench.core.openocd_service.stop_openocd_daemon", return_value="openocd stopped via telnet pid=unknown") as stop_openocd:
            message = stop_monitor_daemon(self.cfg)

        stop_openocd.assert_called_once_with(self.cfg)
        self.assertEqual(message, "monitor not running; openocd stopped via telnet pid=unknown")

    def test_fast_sampling_batches_contiguous_memory_and_buffers_writes(self) -> None:
        engine, fake = self._engine()
        engine.items = [
            {"name": "g_data", "source": "symbol", "symbol": "g_data", "value_type": "u32"},
            {"name": "g_data1", "source": "symbol", "symbol": "g_data1", "value_type": "float"},
            {"name": "g_data_dup", "source": "memory", "target": "0x200001b0", "value_type": "u32"},
        ]
        engine.symbols = {"g_data": 0x200001B0, "g_data1": 0x200001B4}
        engine._memory_reads.clear()
        engine._register_items.clear()
        engine._memory_groups.clear()
        engine._prepare_read_plan()
        engine._init_files()

        rows = engine._sample_items_fast()
        engine._flush_samples()

        self.assertEqual(fake.commands, [])
        self.assertEqual(fake.mem_calls, [(0x200001B0, 32)])
        self.assertEqual(len(rows), 3)
        self.assertEqual(engine.paths.wide_csv_path.read_text(encoding="utf-8").splitlines()[1].count(","), 5)

    def test_probe_once_runs_connect_commands_and_collects_all_item_types(self) -> None:
        engine, fake = self._engine()
        engine.items = [
            {"name": "g_data", "source": "symbol", "symbol": "g_data", "value_type": "u32"},
            {"name": "odr", "source": "memory", "target": "0x4001080c", "value_type": "u16"},
            {"name": "pc", "source": "register", "target": "pc", "value_type": "u32"},
        ]
        engine.symbols = {"g_data": 0x200001B0}

        code, details = engine.probe_once()

        self.assertEqual(code, 0)
        self.assertEqual(fake.commands[0], "targets stm32h7x.cpu0")
        self.assertEqual(len(details["items"]), 3)
        self.assertEqual(details["items"][0]["resolved_address"], "0x200001b0")
        self.assertEqual(details["items"][0]["raw_value_hex"], "0xfffffffe")
        self.assertEqual(details["items"][1]["resolved_address"], "0x4001080c")
        self.assertEqual(details["items"][2]["name"], "pc")
        self.assertTrue(details["items"][2]["ok"])

    def test_symbol_loader_accepts_axf_when_binary_is_elf(self) -> None:
        sample_elf = Path(__file__).resolve().parents[2] / "build" / "cmake-debug" / "serial.elf"
        if not sample_elf.exists():
            self.skipTest("serial.elf sample not available")
        sample_axf = self.temp_dir / "serial_probe.axf"
        shutil.copyfile(sample_elf, sample_axf)
        self.cfg["monitor"]["symbols"]["path"] = str(sample_axf)
        self.cfg["monitor"]["symbols"]["elf_path"] = str(sample_axf)

        engine = MonitorEngine(self.cfg, self.temp_dir)

        self.assertIn("g_data", engine.symbols)


if __name__ == "__main__":
    unittest.main()
