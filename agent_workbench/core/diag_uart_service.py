from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .utils import command_exists, ensure_dir, utc_now_iso

try:
    import serial  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - env specific
    serial = None
    SERIAL_IMPORT_ERROR = exc
else:
    SERIAL_IMPORT_ERROR = None


@dataclass
class DiagExchangeResult:
    exit_code: int
    request_hex: str
    response_hex: str
    log_path: Path


def diag_exchange_supported() -> bool:
    return serial is not None or _powershell_available()


def parse_hex_bytes(text: str) -> bytes:
    cleaned = str(text or "").strip()
    if not cleaned:
        raise ValueError("hex payload is empty")

    normalized = cleaned
    for old, new in [(",", " "), ("-", " "), ("\r", " "), ("\n", " "), ("\t", " ")]:
        normalized = normalized.replace(old, new)
    tokens = [token.strip() for token in normalized.split(" ") if token.strip()]
    if tokens:
        if len(tokens) == 1:
            solo = tokens[0][2:] if tokens[0].lower().startswith("0x") else tokens[0]
            if len(solo) > 2 and len(solo) % 2 == 0:
                return bytes.fromhex(solo)
        values: list[int] = []
        for token in tokens:
            item = token[2:] if token.lower().startswith("0x") else token
            if not item:
                raise ValueError(f"invalid hex token: {token}")
            if len(item) > 2:
                raise ValueError(f"hex byte token too long: {token}")
            values.append(int(item, 16))
        return bytes(values)

    compact = cleaned.replace(" ", "")
    compact = compact[2:] if compact.lower().startswith("0x") else compact
    if len(compact) % 2 != 0:
        raise ValueError("hex payload must contain an even number of digits")
    return bytes.fromhex(compact)


def format_hex_bytes(data: bytes) -> str:
    return " ".join(f"{byte:02X}" for byte in data)


def append_modbus_crc(data: bytes) -> bytes:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return data + bytes((crc & 0xFF, (crc >> 8) & 0xFF))


def execute_diag_exchange(
    cfg: dict,
    hex_payload: str,
    log_path: Path,
    *,
    append_crc: str = "",
    response_timeout_sec: float | None = None,
    expected_length: int = 0,
) -> DiagExchangeResult:
    diag_cfg = cfg["diag_uart"]
    request_bytes = parse_hex_bytes(hex_payload)
    crc_mode = str(append_crc or diag_cfg.get("default_crc", "none")).strip().lower()
    timeout_sec = float(response_timeout_sec or diag_cfg.get("response_timeout_sec", 1.0))
    silence_timeout_sec = float(diag_cfg.get("silence_timeout_sec", 0.05))
    read_timeout_sec = float(diag_cfg.get("read_timeout_sec", 0.02))

    if crc_mode == "modbus":
        request_bytes = append_modbus_crc(request_bytes)
    elif crc_mode not in {"", "none"}:
        raise ValueError(f"unsupported CRC mode: {append_crc}")

    ensure_dir(log_path.parent)
    log_path.write_text("", encoding="utf-8")
    if serial is None:
        if not _powershell_available():
            raise RuntimeError(f"diagnostic UART requires pyserial or PowerShell serial support: {SERIAL_IMPORT_ERROR}")
        return _powershell_diag_exchange(
            cfg,
            request_bytes,
            log_path,
            response_timeout_sec=timeout_sec,
            silence_timeout_sec=silence_timeout_sec,
            expected_length=expected_length,
        )

    with serial.Serial(
        diag_cfg["port"],
        int(diag_cfg["baudrate"]),
        timeout=read_timeout_sec,
    ) as ser, log_path.open("w", encoding="utf-8") as fp:
        for method_name in ("reset_input_buffer", "reset_output_buffer"):
            method = getattr(ser, method_name, None)
            if callable(method):
                method()

        request_hex = format_hex_bytes(request_bytes)
        fp.write(
            f"[{utc_now_iso()}] [diag] start port={diag_cfg['port']} baud={diag_cfg['baudrate']} "
            f"timeout={timeout_sec:.3f}s silence={silence_timeout_sec:.3f}s\n"
        )
        fp.write(f"[{utc_now_iso()}] > {request_hex}\n")
        ser.write(request_bytes)
        ser.flush()

        response_bytes = _read_diag_response(
            ser,
            timeout_sec=timeout_sec,
            silence_timeout_sec=silence_timeout_sec,
            expected_length=expected_length,
        )
        if response_bytes:
            response_hex = format_hex_bytes(response_bytes)
            fp.write(f"[{utc_now_iso()}] < {response_hex}\n")
            exit_code = 0
        else:
            response_hex = ""
            fp.write(f"[{utc_now_iso()}] < [timeout]\n")
            exit_code = 41
        fp.write(f"[{utc_now_iso()}] [diag] stop\n")

    return DiagExchangeResult(
        exit_code=exit_code,
        request_hex=request_hex,
        response_hex=response_hex,
        log_path=log_path,
    )


def _powershell_available() -> bool:
    return command_exists("powershell") or command_exists("powershell.exe")


def _read_diag_response(
    ser,
    *,
    timeout_sec: float,
    silence_timeout_sec: float,
    expected_length: int,
) -> bytes:
    response = bytearray()
    deadline = time.time() + timeout_sec
    last_rx_at: float | None = None

    while time.time() < deadline:
        waiting = getattr(ser, "in_waiting", 0)
        size = int(waiting) if isinstance(waiting, int) and waiting > 0 else 1
        chunk = ser.read(size)
        if chunk:
            response.extend(chunk)
            last_rx_at = time.time()
            if expected_length > 0 and len(response) >= expected_length:
                break
            continue
        if response and last_rx_at is not None and (time.time() - last_rx_at) >= silence_timeout_sec:
            break

    return bytes(response)


def _powershell_runtime_dir(cfg: dict) -> Path:
    return ensure_dir(cfg["outputs"]["runtime_root_path"] / "tmp")


def _powershell_diag_exchange(
    cfg: dict,
    request_bytes: bytes,
    log_path: Path,
    *,
    response_timeout_sec: float,
    silence_timeout_sec: float,
    expected_length: int,
) -> DiagExchangeResult:
    runtime_dir = _powershell_runtime_dir(cfg)
    request_path = runtime_dir / "diag_request.json"
    result_path = runtime_dir / "diag_result.json"
    script_path = runtime_dir / "diag_exchange_backend.ps1"
    diag_cfg = cfg["diag_uart"]
    request_path.write_text(json.dumps(list(request_bytes)), encoding="utf-8")
    try:
        result_path.unlink(missing_ok=True)
    except TypeError:
        if result_path.exists():
            result_path.unlink()
    script_path.write_text(
        r"""
param(
  [string]$Port,
  [int]$Baudrate,
  [string]$RequestFile,
  [string]$ResultFile,
  [string]$LogPath,
  [int]$ReadTimeoutMs,
  [int]$ResponseTimeoutMs,
  [int]$SilenceTimeoutMs,
  [int]$ExpectedLength
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$raw = Get-Content -Raw -Path $RequestFile -Encoding UTF8 | ConvertFrom-Json
$request = New-Object byte[] $raw.Count
for ($i = 0; $i -lt $raw.Count; $i++) {
  $request[$i] = [byte]$raw[$i]
}
$serial = New-Object System.IO.Ports.SerialPort $Port, $Baudrate, ([System.IO.Ports.Parity]::None), 8, ([System.IO.Ports.StopBits]::One)
$serial.ReadTimeout = $ReadTimeoutMs
$response = New-Object System.Collections.Generic.List[byte]
$exitCode = 0

function Get-Timestamp {
  return [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffzzz")
}

function Append-Utf8([string]$path, [string]$line) {
  $writer = New-Object System.IO.StreamWriter($path, $true, (New-Object System.Text.UTF8Encoding($false)))
  try {
    $writer.WriteLine($line)
  } finally {
    $writer.Dispose()
  }
}

function Format-Hex([System.Collections.Generic.List[byte]]$bytes) {
  if (($null -eq $bytes) -or ($bytes.Count -eq 0)) {
    return ""
  }
  return [string]::Join(" ", ($bytes | ForEach-Object { "{0:X2}" -f $_ }))
}

function Format-Request([byte[]]$bytes) {
  return [string]::Join(" ", ($bytes | ForEach-Object { "{0:X2}" -f $_ }))
}

try {
  $serial.Open()
  $serial.DiscardInBuffer()
  $serial.DiscardOutBuffer()
  Append-Utf8 $LogPath ("[{0}] [diag] start port={1} baud={2} backend=powershell" -f (Get-Timestamp), $Port, $Baudrate)
  Append-Utf8 $LogPath ("[{0}] > {1}" -f (Get-Timestamp), (Format-Request $request))
  $serial.Write($request, 0, $request.Length)

  $deadline = [DateTime]::UtcNow.AddMilliseconds($ResponseTimeoutMs)
  $lastByteAt = $null
  while ([DateTime]::UtcNow -lt $deadline) {
    try {
      $next = $serial.ReadByte()
      if ($next -ge 0) {
        $response.Add([byte]$next)
        $lastByteAt = [DateTime]::UtcNow
        if (($ExpectedLength -gt 0) -and ($response.Count -ge $ExpectedLength)) {
          break
        }
        continue
      }
    } catch [System.TimeoutException] {
    }

    if (($response.Count -gt 0) -and ($null -ne $lastByteAt)) {
      if (([DateTime]::UtcNow - $lastByteAt).TotalMilliseconds -ge $SilenceTimeoutMs) {
        break
      }
    }
  }

  if ($response.Count -gt 0) {
    Append-Utf8 $LogPath ("[{0}] < {1}" -f (Get-Timestamp), (Format-Hex $response))
  } else {
    Append-Utf8 $LogPath ("[{0}] < [timeout]" -f (Get-Timestamp))
    $exitCode = 41
  }
} finally {
  if ($serial.IsOpen) {
    $serial.Close()
  }
  Append-Utf8 $LogPath ("[{0}] [diag] stop" -f (Get-Timestamp))
}

[ordered]@{
  exit_code = $exitCode
  response_hex = (Format-Hex $response)
} | ConvertTo-Json -Depth 4 | Set-Content -Path $ResultFile -Encoding UTF8
""".strip()
        + "\n",
        encoding="utf-8",
    )
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                "-Port",
                str(diag_cfg["port"]),
                "-Baudrate",
                str(int(diag_cfg["baudrate"])),
                "-RequestFile",
                str(request_path),
                "-ResultFile",
                str(result_path),
                "-LogPath",
                str(log_path),
                "-ReadTimeoutMs",
                str(max(10, int(float(diag_cfg.get("read_timeout_sec", 0.02)) * 1000))),
                "-ResponseTimeoutMs",
                str(max(100, int(response_timeout_sec * 1000))),
                "-SilenceTimeoutMs",
                str(max(10, int(silence_timeout_sec * 1000))),
                "-ExpectedLength",
                str(max(0, int(expected_length))),
            ],
            check=False,
            cwd=str(cfg["project_root_path"]),
            capture_output=True,
            text=True,
            timeout=max(10.0, response_timeout_sec + 5.0),
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"PowerShell diagnostic backend timed out while opening or reading {diag_cfg['port']}"
        ) from exc
    if (completed.returncode != 0) and (not result_path.exists()):
        raise RuntimeError(
            "PowerShell diagnostic backend failed before producing a result file: "
            f"returncode={completed.returncode} stderr={completed.stderr.strip()}"
        )
    if not result_path.exists():
        raise RuntimeError(
            "PowerShell diagnostic backend did not produce a result file: "
            f"returncode={completed.returncode} stderr={completed.stderr.strip()}"
        )
    payload = json.loads(result_path.read_text(encoding="utf-8-sig"))
    return DiagExchangeResult(
        exit_code=int(payload.get("exit_code", 1)),
        request_hex=format_hex_bytes(request_bytes),
        response_hex=str(payload.get("response_hex", "")),
        log_path=log_path,
    )
