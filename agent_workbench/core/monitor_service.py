from __future__ import annotations

import csv
import ctypes
import json
import os
import subprocess
import sys
import struct
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .openocd_client import OpenOcdClient, OpenOcdConfig
from .symbols import load_symbols
from .utils import (
    append_jsonl,
    clear_pid_file,
    ensure_dir,
    is_process_alive,
    read_pid,
    spawn_detached_command_with_stdin_keeper,
    terminate_process,
    utc_now_iso,
    write_pid,
)


def _to_u32(raw: int) -> int:
    return raw & 0xFFFFFFFF


def _to_s32(raw: int) -> int:
    raw = _to_u32(raw)
    if raw & 0x80000000:
        return -((~raw + 1) & 0xFFFFFFFF)
    return raw


def _to_s16(raw: int) -> int:
    raw = raw & 0xFFFF
    if raw & 0x8000:
        return -((~raw + 1) & 0xFFFF)
    return raw


def _to_s8(raw: int) -> int:
    raw = raw & 0xFF
    if raw & 0x80:
        return -((~raw + 1) & 0xFF)
    return raw


def _to_float(raw: int) -> float:
    return struct.unpack("<f", struct.pack("<I", _to_u32(raw)))[0]


def _parse_number(value) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not a valid numeric address")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value.strip(), 0)
    return int(value)


def _can_parse_number(value) -> bool:
    try:
        _parse_number(value)
    except Exception:
        return False
    return True


def _value_width_bits(value_type: str) -> int:
    normalized = value_type.lower()
    if normalized in {"u8", "s8"}:
        return 8
    if normalized in {"u16", "s16"}:
        return 16
    return 32


def _convert_value(raw: int, value_type: str):
    normalized = value_type.lower()
    if normalized == "u32":
        return _to_u32(raw)
    if normalized == "s32":
        return _to_s32(raw)
    if normalized == "float":
        return _to_float(raw)
    if normalized == "u16":
        return _to_u32(raw) & 0xFFFF
    if normalized == "s16":
        return _to_s16(raw)
    if normalized == "u8":
        return _to_u32(raw) & 0xFF
    if normalized == "s8":
        return _to_s8(raw)
    return _to_u32(raw)


def _json_string(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def _json_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _csv_safe(value: object) -> str:
    return str(value).replace("\x00", "")


@dataclass
class MonitorPaths:
    csv_path: Path
    wide_csv_path: Path
    jsonl_path: Path
    snapshot_path: Path
    meta_path: Path
    stop_request_path: Path


@dataclass
class MemoryRead:
    address: int
    width_bits: int
    value_type: str


@dataclass
class MemoryReadGroup:
    address: int
    width_bits: int
    count: int
    addresses: list[int]


def _truthy(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _begin_high_resolution_timer() -> bool:
    if os.name != "nt":
        return False
    try:
        return ctypes.windll.winmm.timeBeginPeriod(1) == 0  # type: ignore[attr-defined]
    except Exception:
        return False


def _end_high_resolution_timer(enabled: bool) -> None:
    if not enabled or os.name != "nt":
        return
    try:
        ctypes.windll.winmm.timeEndPeriod(1)  # type: ignore[attr-defined]
    except Exception:
        pass


def _wait_until(deadline: float) -> None:
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            return
        if remaining > 0.003:
            time.sleep(remaining - 0.001)
        elif remaining > 0.0005:
            time.sleep(0)


class MonitorEngine:
    def __init__(self, cfg: dict, out_dir: Path):
        self.cfg = cfg
        self.items = cfg["monitor"].get("items", [])
        self.sample_hz = max(1, int(cfg["monitor"].get("sample_hz", 10)))
        self.register_sample_hz = max(0, int(cfg["monitor"].get("register_sample_hz", 10)))
        self.ring_size = max(1, int(cfg["monitor"].get("ring_size", 2000)))
        self.export_interval_sec = max(1, int(cfg["monitor"].get("export_interval_sec", 3)))
        self.flush_interval_sec = max(0.001, float(cfg["monitor"].get("flush_interval_sec", 0.05)))
        self.read_while_running = _truthy(cfg["monitor"].get("read_while_running", True), default=True)
        self.halt_per_sample = _truthy(cfg["monitor"].get("halt_per_sample", False), default=False)
        self.out_dir = ensure_dir(out_dir)
        self.paths = MonitorPaths(
            csv_path=self.out_dir / "monitor_samples.csv",
            wide_csv_path=self.out_dir / "monitor_samples_wide.csv",
            jsonl_path=self.out_dir / "monitor_samples.jsonl",
            snapshot_path=self.out_dir / "monitor_snapshot.csv",
            meta_path=self.out_dir / "monitor_session.jsonl",
            stop_request_path=self.out_dir / "monitor.stop",
        )
        ocd_cfg = cfg["monitor"]["openocd"]
        self.openocd = OpenOcdClient(
            OpenOcdConfig(
                host=ocd_cfg.get("host", "127.0.0.1"),
                port=int(ocd_cfg.get("port", 4444)),
                timeout_sec=float(ocd_cfg.get("timeout_sec", 2.0)),
                post_command_drain_sec=float(ocd_cfg.get("post_command_drain_sec", 0.0)),
            )
        )
        self.stop_event = threading.Event()
        self.ring: dict[str, deque[tuple[str, object, bool, str]]] = defaultdict(
            lambda: deque(maxlen=self.ring_size)
        )
        self.symbols = load_symbols(cfg, monitor=True)
        self._start_perf: float | None = None
        self._sample_count = 0
        self._last_register_sample_perf = 0.0
        self._last_values: dict[str, tuple[object, bool, str]] = {}
        self._pending_long_rows: list[list[object]] = []
        self._pending_json_rows: list[dict[str, object]] = []
        self._pending_wide_rows: list[list[object]] = []
        self._memory_reads: dict[str, MemoryRead] = {}
        self._register_items: list[dict] = []
        self._memory_groups: list[MemoryReadGroup] = []
        self._prepare_read_plan()

    def _apply_connect_commands(self) -> list[str]:
        commands = self.cfg["monitor"]["openocd"].get("connect_commands", [])
        return self.openocd.run_commands(commands)

    def _resolve_address(self, item: dict) -> int:
        source = item.get("source", "").lower()
        if source in {"memory", "address", "register"}:
            if "address" in item:
                return _parse_number(item["address"])
            if "target" in item and _can_parse_number(item["target"]):
                return _parse_number(item["target"])
            if "symbol" in item:
                symbol = item["symbol"]
                if symbol not in self.symbols:
                    raise RuntimeError(f"symbol not found in symbol image: {symbol}")
                return self.symbols[symbol] + _parse_number(item.get("offset", 0))
            if source == "register":
                raise RuntimeError("register item needs a CPU register target or a numeric address")
            raise RuntimeError("memory/address item needs target, address, or symbol")
        if source == "symbol":
            symbol = item["symbol"]
            if symbol not in self.symbols:
                raise RuntimeError(f"symbol not found in symbol image: {symbol}")
            return self.symbols[symbol] + _parse_number(item.get("offset", 0))
        raise RuntimeError(f"unsupported source for address resolving: {source}")

    def _read_item(self, item: dict):
        source = item.get("source", "").lower()
        value_type = item.get("value_type", "u32")
        if source in {"register", "cpu_register"} and "address" not in item and not _can_parse_number(item.get("target", "")):
            raw = self.openocd.read_register(item["target"])
        else:
            raw = self.openocd.read_mem_value(self._resolve_address(item), width_bits=_value_width_bits(value_type))
        return raw, _convert_value(raw, value_type)

    def _describe_items(self) -> list[dict[str, object]]:
        described: list[dict[str, object]] = []
        for item in self.items:
            entry: dict[str, object] = {
                "name": item.get("name", "unnamed"),
                "source": item.get("source", ""),
                "value_type": item.get("value_type", "u32"),
                "width_bits": _value_width_bits(item.get("value_type", "u32")),
            }
            source = str(item.get("source", "")).lower()
            if source in {"register", "cpu_register"} and "address" not in item and not _can_parse_number(item.get("target", "")):
                entry["target"] = item.get("target", "")
            else:
                try:
                    entry["resolved_address"] = f"0x{self._resolve_address(item):08x}"
                except Exception as exc:
                    entry["resolve_error"] = str(exc)
            if "symbol" in item:
                entry["symbol"] = item.get("symbol", "")
            if "offset" in item:
                entry["offset"] = item.get("offset", 0)
            described.append(entry)
        return described

    def _prepare_read_plan(self) -> None:
        reads_by_key: dict[tuple[int, int], MemoryRead] = {}
        for item in self.items:
            source = str(item.get("source", "")).lower()
            if source in {"register", "cpu_register"} and "address" not in item and not _can_parse_number(item.get("target", "")):
                self._register_items.append(item)
                continue
            value_type = str(item.get("value_type", "u32"))
            width_bits = _value_width_bits(value_type)
            try:
                address = self._resolve_address(item)
            except Exception:
                continue
            read = reads_by_key.setdefault((address, width_bits), MemoryRead(address, width_bits, value_type))
            self._memory_reads[str(item.get("name", "unnamed"))] = read

        for width_bits in sorted({read.width_bits for read in reads_by_key.values()}):
            addresses = sorted(read.address for read in reads_by_key.values() if read.width_bits == width_bits)
            if not addresses:
                continue
            step = max(1, width_bits // 8)
            run = [addresses[0]]
            for address in addresses[1:]:
                if address == run[-1] + step:
                    run.append(address)
                else:
                    self._memory_groups.append(MemoryReadGroup(run[0], width_bits, len(run), list(run)))
                    run = [address]
            self._memory_groups.append(MemoryReadGroup(run[0], width_bits, len(run), list(run)))

    def _init_files(self) -> None:
        self._start_perf = time.perf_counter()
        self._sample_count = 0
        self._last_register_sample_perf = 0.0
        self._last_values.clear()
        self._pending_long_rows.clear()
        self._pending_json_rows.clear()
        self._pending_wide_rows.clear()
        try:
            self.paths.stop_request_path.unlink(missing_ok=True)
        except TypeError:
            if self.paths.stop_request_path.exists():
                self.paths.stop_request_path.unlink()
        with self.paths.csv_path.open("w", encoding="utf-8", newline="") as fp:
            csv.writer(fp).writerow(["sample_index", "elapsed_ms", "ts", "item", "value", "ok", "message"])
        with self.paths.wide_csv_path.open("w", encoding="utf-8", newline="") as fp:
            csv.writer(fp).writerow(["sample_index", "elapsed_ms", "ts", *[str(item.get("name", "unnamed")) for item in self.items]])
        self.paths.jsonl_path.write_text("", encoding="utf-8")
        self.paths.meta_path.write_text("", encoding="utf-8")
        append_jsonl(
            self.paths.meta_path,
            {
                "ts": utc_now_iso(),
                "event": "monitor_start",
                "items": self._describe_items(),
                "sample_hz": self.sample_hz,
                "sample_interval_ms": 1000.0 / self.sample_hz,
                "read_while_running": self.read_while_running,
                "halt_per_sample": self.halt_per_sample,
                "register_sample_hz": self.register_sample_hz,
                "flush_interval_sec": self.flush_interval_sec,
                "memory_read_groups": [
                    {
                        "address": f"0x{group.address:08x}",
                        "width_bits": group.width_bits,
                        "count": group.count,
                    }
                    for group in self._memory_groups
                ],
                "symbol_image": str(self.cfg["monitor"]["symbols"]["path"]),
                "connect_commands": list(self.cfg["monitor"]["openocd"].get("connect_commands", [])),
                "note": "symbol addresses are resolved from monitor.symbols.path; flash the same symbol image before monitoring",
            },
        )

    def _elapsed_ms(self) -> float:
        if self._start_perf is None:
            return 0.0
        return (time.perf_counter() - self._start_perf) * 1000.0

    def _append_samples(self, ts: str, elapsed_ms: float, rows: list[dict[str, object]]) -> None:
        sample_index = self._sample_count
        for row in rows:
            message = _csv_safe(row["message"])
            self._pending_long_rows.append(
                [sample_index, f"{elapsed_ms:.6f}", ts, row["item"], row["value"], int(bool(row["ok"])), message]
            )
            self._pending_json_rows.append(
                {
                    "sample_index": sample_index,
                    "ts": ts,
                    "elapsed_ms": round(elapsed_ms, 6),
                    "item": row["item"],
                    "value": row["value"],
                    "ok": bool(row["ok"]),
                    "message": message,
                }
            )
        values_by_name = {str(row["item"]): row["value"] if bool(row["ok"]) else "" for row in rows}
        self._pending_wide_rows.append(
            [
                sample_index,
                f"{elapsed_ms:.6f}",
                ts,
                *[values_by_name.get(str(item.get("name", "unnamed")), "") for item in self.items],
            ]
        )
        for row in rows:
            item_name = str(row["item"])
            self.ring[item_name].append((ts, row["value"], bool(row["ok"]), _csv_safe(row["message"])))

    def _flush_samples(self) -> None:
        if self._pending_long_rows:
            with self.paths.csv_path.open("a", encoding="utf-8", newline="") as fp:
                csv.writer(fp).writerows(self._pending_long_rows)
            self._pending_long_rows.clear()
        if self._pending_json_rows:
            with self.paths.jsonl_path.open("a", encoding="utf-8") as fp:
                for row in self._pending_json_rows:
                    fp.write(json.dumps(row, ensure_ascii=False) + "\n")
            self._pending_json_rows.clear()
        if self._pending_wide_rows:
            with self.paths.wide_csv_path.open("a", encoding="utf-8", newline="") as fp:
                csv.writer(fp).writerows(self._pending_wide_rows)
            self._pending_wide_rows.clear()

    def _read_memory_batch(self) -> dict[tuple[int, int], int]:
        values: dict[tuple[int, int], int] = {}
        for group in self._memory_groups:
            raws = self.openocd.read_mem(group.address, group.count, width_bits=group.width_bits)
            for address, raw in zip(group.addresses, raws):
                values[(address, group.width_bits)] = raw
        return values

    def _registers_due(self) -> bool:
        if not self._register_items or self.register_sample_hz <= 0:
            return False
        now = time.perf_counter()
        if self._last_register_sample_perf <= 0:
            return True
        return now - self._last_register_sample_perf >= (1.0 / self.register_sample_hz)

    def _sample_items_fast(self, *, persist: bool = True) -> list[dict[str, object]]:
        ts = utc_now_iso()
        elapsed_ms = self._elapsed_ms()
        persisted_rows: list[dict[str, object]] = []
        sample_rows: list[dict[str, object]] = []
        raw_values: dict[tuple[int, int], int] = {}
        register_due = self._registers_due()
        need_halt = self.halt_per_sample or not self.read_while_running or (register_due and bool(self._register_items))
        halted = False

        try:
            if need_halt:
                self.openocd.halt()
                halted = True
            raw_values = self._read_memory_batch()
        except Exception as exc:
            for item in self.items:
                source = str(item.get("source", "")).lower()
                is_cpu_register = source in {"register", "cpu_register"} and "address" not in item and not _can_parse_number(item.get("target", ""))
                if not is_cpu_register:
                    self._last_values[str(item.get("name", "unnamed"))] = ("", False, str(exc))

        for item in self.items:
            item_name = str(item.get("name", "unnamed"))
            source = str(item.get("source", "")).lower()
            value_type = str(item.get("value_type", "u32"))
            is_cpu_register = source in {"register", "cpu_register"} and "address" not in item and not _can_parse_number(item.get("target", ""))
            raw = None
            if is_cpu_register:
                if register_due:
                    try:
                        raw = self.openocd.read_register(str(item.get("target", "")))
                        value = _convert_value(raw, value_type)
                        ok = True
                        message = ""
                        self._last_values[item_name] = (value, ok, message)
                    except Exception as exc:
                        value, ok, message = ("", False, str(exc))
                        self._last_values[item_name] = (value, ok, message)
                else:
                    value, ok, message = self._last_values.get(item_name, ("", False, "register refresh pending"))
                    if ok:
                        message = "held"
            else:
                read = self._memory_reads.get(item_name)
                try:
                    if read is None:
                        raise RuntimeError("item was not included in the memory read batch")
                    raw = raw_values[(read.address, read.width_bits)]
                    value = _convert_value(raw, value_type)
                    ok = True
                    message = ""
                    self._last_values[item_name] = (value, ok, message)
                except Exception as exc:
                    value, ok, message = self._last_values.get(item_name, ("", False, str(exc)))
                    if ok:
                        message = "held"

            persisted_rows.append({"item": item_name, "value": value, "ok": ok, "message": message})
            entry: dict[str, object] = {
                "name": item_name,
                "source": source,
                "value": value,
                "ok": ok,
                "error": "" if ok else str(message),
                "value_type": value_type,
                "width_bits": _value_width_bits(value_type),
            }
            if raw is not None:
                entry["raw_value_hex"] = f"0x{_to_u32(raw):08x}"
            if "target" in item:
                entry["target"] = item.get("target", "")
            if "symbol" in item:
                entry["symbol"] = item.get("symbol", "")
            if "offset" in item:
                entry["offset"] = item.get("offset", 0)
            if not is_cpu_register:
                try:
                    entry["resolved_address"] = f"0x{self._resolve_address(item):08x}"
                except Exception as exc:
                    entry["resolve_error"] = str(exc)
            sample_rows.append(entry)

        if register_due:
            self._last_register_sample_perf = time.perf_counter()
        if halted:
            try:
                self.openocd.resume()
            except Exception:
                pass
        if persist:
            self._append_samples(ts, elapsed_ms, persisted_rows)
            self._sample_count += 1
        return sample_rows

    def _dump_snapshot(self) -> None:
        with self.paths.snapshot_path.open("w", encoding="utf-8", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(["item", "index", "ts", "value", "ok", "message"])
            for item_name, samples in self.ring.items():
                for index, (ts, value, ok, message) in enumerate(samples):
                    writer.writerow([item_name, index, ts, value, int(ok), message])

    def _sample_items(self, *, persist: bool = True) -> list[dict[str, object]]:
        ts = utc_now_iso()
        elapsed_ms = self._elapsed_ms()
        halted = False
        persisted_rows: list[dict[str, object]] = []
        sample_rows: list[dict[str, object]] = []
        try:
            self.openocd.halt()
            halted = True
        except Exception:
            pass

        for item in self.items:
            item_name = item.get("name", "unnamed")
            try:
                raw, value = self._read_item(item)
                persisted_rows.append(
                    {
                        "item": item_name,
                        "value": value,
                        "ok": True,
                        "message": "",
                        "ts_json": _json_string(ts),
                        "item_json": _json_string(item_name),
                        "value_json": _json_value(value),
                        "message_json": _json_string(""),
                    }
                )
                entry: dict[str, object] = {
                    "name": item_name,
                    "source": item.get("source", ""),
                    "value": value,
                    "raw_value_hex": f"0x{_to_u32(raw):08x}",
                    "ok": True,
                    "error": "",
                    "value_type": item.get("value_type", "u32"),
                    "width_bits": _value_width_bits(item.get("value_type", "u32")),
                }
            except Exception as exc:
                persisted_rows.append(
                    {
                        "item": item_name,
                        "value": "",
                        "ok": False,
                        "message": str(exc),
                        "ts_json": _json_string(ts),
                        "item_json": _json_string(item_name),
                        "value_json": _json_value(""),
                        "message_json": _json_string(str(exc)),
                    }
                )
                entry = {
                    "name": item_name,
                    "source": item.get("source", ""),
                    "value": "",
                    "ok": False,
                    "error": str(exc),
                    "value_type": item.get("value_type", "u32"),
                    "width_bits": _value_width_bits(item.get("value_type", "u32")),
                }
            if "target" in item:
                entry["target"] = item.get("target", "")
            if "symbol" in item:
                entry["symbol"] = item.get("symbol", "")
            if "offset" in item:
                entry["offset"] = item.get("offset", 0)
            source = str(item.get("source", "")).lower()
            if source not in {"register", "cpu_register"} or "address" in item or _can_parse_number(item.get("target", "")):
                try:
                    entry["resolved_address"] = f"0x{self._resolve_address(item):08x}"
                except Exception as exc:
                    entry["resolve_error"] = str(exc)
            sample_rows.append(entry)

        if halted:
            try:
                self.openocd.resume()
            except Exception:
                pass
        if persist:
            self._append_samples(ts, elapsed_ms, persisted_rows)
            self._sample_count += 1
        return sample_rows

    def probe_once(self) -> tuple[int, dict[str, object]]:
        details: dict[str, object] = {
            "symbol_image": str(self.cfg["monitor"]["symbols"]["path"]),
            "connect_commands": list(self.cfg["monitor"]["openocd"].get("connect_commands", [])),
            "items": [],
        }
        try:
            self.openocd.connect()
            details["connect_ok"] = True
        except Exception as exc:
            details["connect_ok"] = False
            details["error"] = str(exc)
            return 2, details

        try:
            outputs = self._apply_connect_commands()
            if outputs:
                details["connect_outputs"] = [item.strip() for item in outputs]
            details["items"] = self._sample_items(persist=False)
            return 0, details
        except Exception as exc:
            details["error"] = str(exc)
            return 3, details
        finally:
            try:
                self.openocd.resume()
            except Exception:
                pass
            self.openocd.close()

    def run(self, *, reset_first: bool = False) -> int:
        try:
            self.openocd.connect()
        except Exception as exc:
            ensure_dir(self.paths.meta_path.parent)
            append_jsonl(self.paths.meta_path, {"ts": utc_now_iso(), "event": "openocd_connect_failed", "error": str(exc)})
            return 2
        self._init_files()

        try:
            outputs = self._apply_connect_commands()
            if outputs:
                append_jsonl(
                    self.paths.meta_path,
                    {"ts": utc_now_iso(), "event": "openocd_connect_commands", "outputs": [item.strip() for item in outputs]},
                )
        except Exception as exc:
            append_jsonl(self.paths.meta_path, {"ts": utc_now_iso(), "event": "openocd_connect_commands_failed", "error": str(exc)})
            self.openocd.close()
            return 3

        if reset_first:
            try:
                self.openocd.command("reset run")
                append_jsonl(self.paths.meta_path, {"ts": utc_now_iso(), "event": "target_reset_run"})
            except Exception as exc:
                append_jsonl(self.paths.meta_path, {"ts": utc_now_iso(), "event": "target_reset_failed", "error": str(exc)})
                self.openocd.close()
                return 4
        elif not self.read_while_running:
            try:
                self.openocd.resume()
            except Exception:
                pass

        sample_interval = 1.0 / self.sample_hz
        last_export = time.perf_counter()
        last_flush = time.perf_counter()
        next_tick = time.perf_counter()
        overrun_count = 0
        timer_enabled = _begin_high_resolution_timer()
        try:
            while not self.stop_event.is_set():
                if self.paths.stop_request_path.exists():
                    append_jsonl(self.paths.meta_path, {"ts": utc_now_iso(), "event": "monitor_stop_requested"})
                    break
                self._sample_items_fast()
                if time.perf_counter() - last_export >= self.export_interval_sec:
                    self._flush_samples()
                    self._dump_snapshot()
                    last_export = time.perf_counter()
                if time.perf_counter() - last_flush >= self.flush_interval_sec:
                    self._flush_samples()
                    last_flush = time.perf_counter()
                next_tick += sample_interval
                sleep_for = next_tick - time.perf_counter()
                if sleep_for > 0:
                    _wait_until(next_tick)
                else:
                    overrun_count += 1
                    next_tick = time.perf_counter()
        finally:
            _end_high_resolution_timer(timer_enabled)

        self._flush_samples()
        self._dump_snapshot()
        elapsed_sec = self._elapsed_ms() / 1000.0
        append_jsonl(
            self.paths.meta_path,
            {
                "ts": utc_now_iso(),
                "event": "monitor_stop",
                "sample_count": self._sample_count,
                "elapsed_sec": round(elapsed_sec, 6),
                "actual_sample_hz": round(self._sample_count / elapsed_sec, 3) if elapsed_sec > 0 else 0,
                "target_sample_hz": self.sample_hz,
                "overrun_count": overrun_count,
                "wide_csv": str(self.paths.wide_csv_path),
            },
        )
        try:
            self.openocd.resume()
        except Exception:
            pass
        self.openocd.close()
        try:
            self.paths.stop_request_path.unlink(missing_ok=True)
        except TypeError:
            if self.paths.stop_request_path.exists():
                self.paths.stop_request_path.unlink()
        return 0


def _pid_path(cfg: dict) -> Path:
    return ensure_dir(cfg["outputs"]["runtime_root_path"] / "pids") / "monitor.pid"


def start_monitor_daemon(cfg: dict, config_path: Path, workbench_script: Path, *, reset_first: bool = False) -> str:
    pid_file = _pid_path(cfg)
    old_pid = read_pid(pid_file)
    if old_pid and is_process_alive(old_pid):
        return f"monitor already running pid={old_pid}"
    if old_pid:
        clear_pid_file(pid_file)
    from .openocd_service import start_openocd_daemon

    openocd_message = start_openocd_daemon(cfg)
    out_dir = ensure_dir(cfg["outputs"]["runtime_root_path"] / "monitor_live")
    if "startup timeout" in openocd_message or "unavailable" in openocd_message or "empty" in openocd_message:
        return f"{openocd_message}; monitor not started"
    args = [
        str(workbench_script),
        "__monitor-run",
        "--config",
        str(config_path),
        "--out-dir",
        str(out_dir),
    ]
    if reset_first:
        args.append("--reset-first")
    log_path = out_dir / "monitor_daemon.log"
    command = subprocess.list2cmdline([sys.executable, *args])
    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(f"[{utc_now_iso()}] spawn: {command}\n")
    pid = spawn_detached_command_with_stdin_keeper(command, cwd=cfg["project_root_path"], log_path=log_path)
    write_pid(pid_file, pid)
    reset_note = " reset_first=1" if reset_first else ""
    return f"{openocd_message}; monitor started pid={pid}, out={out_dir}, log={log_path}{reset_note}"


def stop_monitor_daemon(cfg: dict) -> str:
    from .openocd_service import stop_openocd_daemon

    openocd_message = ""
    pid_file = _pid_path(cfg)
    pid = read_pid(pid_file)
    if not pid:
        openocd_message = stop_openocd_daemon(cfg)
        return f"monitor not running; {openocd_message}"
    if not is_process_alive(pid):
        clear_pid_file(pid_file)
        openocd_message = stop_openocd_daemon(cfg)
        return f"monitor stale pid cleaned pid={pid}; {openocd_message}"
    out_dir = ensure_dir(cfg["outputs"]["runtime_root_path"] / "monitor_live")
    stop_request_path = out_dir / "monitor.stop"
    stop_request_path.write_text(utc_now_iso(), encoding="utf-8")
    for _ in range(100):
        if not is_process_alive(pid):
            clear_pid_file(pid_file)
            openocd_message = stop_openocd_daemon(cfg)
            return f"monitor stopped pid={pid}; {openocd_message}"
        time.sleep(0.05)
    terminate_process(pid)
    clear_pid_file(pid_file)
    openocd_message = stop_openocd_daemon(cfg)
    return f"monitor force stopped pid={pid}; {openocd_message}"


def monitor_status(cfg: dict) -> str:
    pid = read_pid(_pid_path(cfg))
    if not pid:
        return "monitor status: stopped"
    return f"monitor status: {'running' if is_process_alive(pid) else 'stale'} pid={pid}"


def export_monitor_table(src: Path, dst: Path) -> str:
    if not src.exists():
        return f"source not found: {src}"
    ensure_dir(dst.parent)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return f"exported: {dst}"


def summarize_monitor_samples(src: Path) -> dict[str, object]:
    if not src.exists():
        return {"ok": False, "error": f"source not found: {src}", "source": str(src)}
    text = src.read_text(encoding="utf-8").replace("\x00", "")
    reader = csv.DictReader(text.splitlines())
    rows = list(reader)
    samples: dict[str, float] = {}
    fallback_index = 0
    for row in rows:
        elapsed_text = str(row.get("elapsed_ms", "")).strip()
        try:
            elapsed_ms = float(elapsed_text)
        except ValueError:
            continue
        sample_key = str(row.get("sample_index", "")).strip()
        if not sample_key:
            sample_key = str(row.get("ts", "")).strip()
        if not sample_key:
            sample_key = str(fallback_index)
            fallback_index += 1
        samples.setdefault(sample_key, elapsed_ms)

    ordered = sorted(samples.values())
    if len(ordered) < 2:
        return {"ok": False, "error": "not enough samples", "source": str(src), "sample_count": len(ordered)}

    deltas = [b - a for a, b in zip(ordered, ordered[1:]) if b >= a]
    elapsed_span_ms = ordered[-1] - ordered[0]
    actual_hz = ((len(ordered) - 1) * 1000.0 / elapsed_span_ms) if elapsed_span_ms > 0 else 0.0
    return {
        "ok": True,
        "source": str(src),
        "sample_count": len(ordered),
        "elapsed_span_ms": round(elapsed_span_ms, 6),
        "actual_sample_hz": round(actual_hz, 3),
        "avg_delta_ms": round((sum(deltas) / len(deltas)) if deltas else 0.0, 6),
        "min_delta_ms": round(min(deltas), 6) if deltas else 0.0,
        "max_delta_ms": round(max(deltas), 6) if deltas else 0.0,
    }


def _elapsed_ms_from_ts(first: datetime | None, ts_text: str) -> tuple[datetime | None, str]:
    try:
        current = datetime.fromisoformat(ts_text.replace("Z", "+00:00"))
    except ValueError:
        return first, ""
    if first is None:
        first = current
    return first, f"{(current - first).total_seconds() * 1000.0:.3f}"


def export_monitor_wide(src: Path, dst: Path) -> str:
    if not src.exists():
        return f"source not found: {src}"
    ensure_dir(dst.parent)
    text = src.read_text(encoding="utf-8").replace("\x00", "")
    reader = csv.DictReader(text.splitlines())
    rows = list(reader)
    item_names: list[str] = []
    sample_order: list[str] = []
    by_sample: dict[str, dict[str, str]] = {}
    first_ts: datetime | None = None
    meta_by_sample: dict[str, tuple[str, str]] = {}
    for row in rows:
        ts = str(row.get("ts", ""))
        item = str(row.get("item", ""))
        if not ts or not item:
            continue
        sample_key = str(row.get("sample_index", "")).strip() or ts
        if sample_key not in by_sample:
            sample_order.append(sample_key)
        if item not in item_names:
            item_names.append(item)
        elapsed_ms = str(row.get("elapsed_ms", "")).strip()
        if not elapsed_ms:
            first_ts, elapsed_ms = _elapsed_ms_from_ts(first_ts, ts)
        meta_by_sample.setdefault(sample_key, (elapsed_ms, ts))
        by_sample.setdefault(sample_key, {})[item] = str(row.get("value", "")) if str(row.get("ok", "1")) == "1" else ""
    with dst.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["sample_index", "elapsed_ms", "ts", *item_names])
        for sample_key in sample_order:
            elapsed_ms, ts = meta_by_sample.get(sample_key, ("", ""))
            values = by_sample.get(sample_key, {})
            writer.writerow([sample_key, elapsed_ms, ts, *[values.get(item, "") for item in item_names]])
    return f"exported wide table: {dst}"
