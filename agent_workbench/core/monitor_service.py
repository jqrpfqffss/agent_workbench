from __future__ import annotations

import csv
import struct
import subprocess
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

from .openocd_client import OpenOcdClient, OpenOcdConfig
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


def _to_float(raw: int) -> float:
    return struct.unpack("<f", struct.pack("<I", _to_u32(raw)))[0]


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
    if normalized == "u8":
        return _to_u32(raw) & 0xFF
    return _to_u32(raw)


def _load_symbols(cfg: dict) -> dict[str, int]:
    elf_path = Path(cfg["monitor"]["symbols"]["elf_path"])
    nm_command = cfg["tools"].get("symbols_nm", "arm-none-eabi-nm")
    if not elf_path.exists():
        return {}
    try:
        output = subprocess.check_output([nm_command, "-n", str(elf_path)], stderr=subprocess.STDOUT, text=True)
    except Exception:
        return {}
    symbols: dict[str, int] = {}
    for line in output.splitlines():
        parts = line.strip().split()
        if len(parts) < 3:
            continue
        try:
            symbols[parts[2]] = int(parts[0], 16)
        except ValueError:
            continue
    return symbols


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
        self.symbols = _load_symbols(cfg)

    def _resolve_address(self, item: dict) -> int:
        source = item.get("source", "").lower()
        if source == "memory":
            target = item["target"]
            return int(target, 0) if isinstance(target, str) else int(target)
        if source == "symbol":
            symbol = item["symbol"]
            if symbol not in self.symbols:
                raise RuntimeError(f"symbol not found in ELF: {symbol}")
            return self.symbols[symbol] + int(item.get("offset", 0))
        raise RuntimeError(f"unsupported source for address resolving: {source}")

    def _read_item(self, item: dict):
        source = item.get("source", "").lower()
        if source == "register":
            raw = self.openocd.read_register(item["target"])
        else:
            raw = self.openocd.read_mem_word(self._resolve_address(item))
        return _convert_value(raw, item.get("value_type", "u32"))

    def _init_files(self) -> None:
        with self.paths.csv_path.open("w", encoding="utf-8", newline="") as fp:
            csv.writer(fp).writerow(["ts", "item", "value", "ok", "message"])
        append_jsonl(self.paths.meta_path, {"ts": utc_now_iso(), "event": "monitor_start"})

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

    def run(self) -> int:
        self._init_files()
        try:
            self.openocd.connect()
        except Exception as exc:
            append_jsonl(self.paths.meta_path, {"ts": utc_now_iso(), "event": "openocd_connect_failed", "error": str(exc)})
            return 2

        sample_interval = 1.0 / self.sample_hz
        last_export = time.time()
        while not self.stop_event.is_set():
            tick_start = time.time()
            ts = utc_now_iso()
            for item in self.items:
                item_name = item.get("name", "unnamed")
                try:
                    value = self._read_item(item)
                    self._append_sample(ts, item_name, value, True, "")
                except Exception as exc:
                    self._append_sample(ts, item_name, "", False, str(exc))
            if time.time() - last_export >= self.export_interval_sec:
                self._dump_snapshot()
                last_export = time.time()
            elapsed = time.time() - tick_start
            time.sleep(max(0.0, sample_interval - elapsed))

        self._dump_snapshot()
        append_jsonl(self.paths.meta_path, {"ts": utc_now_iso(), "event": "monitor_stop"})
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
