from __future__ import annotations

import csv
import struct
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

from .openocd_client import OpenOcdClient, OpenOcdConfig
from .symbols import load_symbols
from .utils import (
    append_jsonl,
    clear_pid_file,
    ensure_dir,
    is_process_alive,
    read_pid,
    spawn_detached_python,
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


@dataclass
class MonitorPaths:
    csv_path: Path
    jsonl_path: Path
    snapshot_path: Path
    meta_path: Path


class MonitorEngine:
    def __init__(self, cfg: dict, out_dir: Path):
        self.cfg = cfg
        self.items = cfg["monitor"].get("items", [])
        self.sample_hz = max(1, int(cfg["monitor"].get("sample_hz", 10)))
        self.ring_size = max(1, int(cfg["monitor"].get("ring_size", 2000)))
        self.export_interval_sec = max(1, int(cfg["monitor"].get("export_interval_sec", 3)))
        self.out_dir = ensure_dir(out_dir)
        self.paths = MonitorPaths(
            csv_path=self.out_dir / "monitor_samples.csv",
            jsonl_path=self.out_dir / "monitor_samples.jsonl",
            snapshot_path=self.out_dir / "monitor_snapshot.csv",
            meta_path=self.out_dir / "monitor_session.jsonl",
        )
        ocd_cfg = cfg["monitor"]["openocd"]
        self.openocd = OpenOcdClient(
            OpenOcdConfig(
                host=ocd_cfg.get("host", "127.0.0.1"),
                port=int(ocd_cfg.get("port", 4444)),
                timeout_sec=float(ocd_cfg.get("timeout_sec", 2.0)),
            )
        )
        self.stop_event = threading.Event()
        self.ring: dict[str, deque[tuple[str, object, bool, str]]] = defaultdict(
            lambda: deque(maxlen=self.ring_size)
        )
        self.symbols = load_symbols(cfg, monitor=True)

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

    def _init_files(self) -> None:
        with self.paths.csv_path.open("w", encoding="utf-8", newline="") as fp:
            csv.writer(fp).writerow(["ts", "item", "value", "ok", "message"])
        self.paths.jsonl_path.write_text("", encoding="utf-8")
        self.paths.meta_path.write_text("", encoding="utf-8")
        append_jsonl(
            self.paths.meta_path,
            {
                "ts": utc_now_iso(),
                "event": "monitor_start",
                "items": self._describe_items(),
                "symbol_image": str(self.cfg["monitor"]["symbols"]["path"]),
                "connect_commands": list(self.cfg["monitor"]["openocd"].get("connect_commands", [])),
                "note": "symbol addresses are resolved from monitor.symbols.path; flash the same symbol image before monitoring",
            },
        )

    def _append_sample(self, ts: str, item_name: str, value, ok: bool, message: str) -> None:
        with self.paths.csv_path.open("a", encoding="utf-8", newline="") as fp:
            csv.writer(fp).writerow([ts, item_name, value, int(ok), message])
        append_jsonl(self.paths.jsonl_path, {"ts": ts, "item": item_name, "value": value, "ok": ok, "message": message})
        self.ring[item_name].append((ts, value, ok, message))

    def _dump_snapshot(self) -> None:
        with self.paths.snapshot_path.open("w", encoding="utf-8", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(["item", "index", "ts", "value", "ok", "message"])
            for item_name, samples in self.ring.items():
                for index, (ts, value, ok, message) in enumerate(samples):
                    writer.writerow([item_name, index, ts, value, int(ok), message])

    def _sample_items(self, *, persist: bool = True) -> list[dict[str, object]]:
        ts = utc_now_iso()
        halted = False
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
                if persist:
                    self._append_sample(ts, item_name, value, True, "")
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
                if persist:
                    self._append_sample(ts, item_name, "", False, str(exc))
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

    def run(self) -> int:
        self._init_files()
        try:
            self.openocd.connect()
        except Exception as exc:
            append_jsonl(self.paths.meta_path, {"ts": utc_now_iso(), "event": "openocd_connect_failed", "error": str(exc)})
            return 2

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

        try:
            self.openocd.resume()
        except Exception:
            pass

        sample_interval = 1.0 / self.sample_hz
        last_export = time.time()
        while not self.stop_event.is_set():
            tick_start = time.time()
            self._sample_items()
            if time.time() - last_export >= self.export_interval_sec:
                self._dump_snapshot()
                last_export = time.time()
            elapsed = time.time() - tick_start
            time.sleep(max(0.0, sample_interval - elapsed))

        self._dump_snapshot()
        append_jsonl(self.paths.meta_path, {"ts": utc_now_iso(), "event": "monitor_stop"})
        try:
            self.openocd.resume()
        except Exception:
            pass
        self.openocd.close()
        return 0


def _pid_path(cfg: dict) -> Path:
    return ensure_dir(cfg["outputs"]["runtime_root_path"] / "pids") / "monitor.pid"


def start_monitor_daemon(cfg: dict, config_path: Path, workbench_script: Path) -> str:
    pid_file = _pid_path(cfg)
    old_pid = read_pid(pid_file)
    if old_pid and is_process_alive(old_pid):
        return f"monitor already running pid={old_pid}"
    if old_pid:
        clear_pid_file(pid_file)
    out_dir = ensure_dir(cfg["outputs"]["runtime_root_path"] / "monitor_live")
    args = [
        str(workbench_script),
        "monitor",
        "run",
        "--config",
        str(config_path),
        "--out-dir",
        str(out_dir),
    ]
    pid = spawn_detached_python(args, cwd=cfg["project_root_path"])
    write_pid(pid_file, pid)
    return f"monitor started pid={pid}, out={out_dir}"


def stop_monitor_daemon(cfg: dict) -> str:
    pid_file = _pid_path(cfg)
    pid = read_pid(pid_file)
    if not pid:
        return "monitor not running"
    if not is_process_alive(pid):
        clear_pid_file(pid_file)
        return f"monitor stale pid cleaned pid={pid}"
    terminate_process(pid)
    clear_pid_file(pid_file)
    return f"monitor stopped pid={pid}"


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
