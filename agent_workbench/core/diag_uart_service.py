from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .utils import command_exists, ensure_dir, utc_now_iso, write_json

try:
    import serial  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - env specific
    serial = None
    SERIAL_IMPORT_ERROR = exc
else:
    SERIAL_IMPORT_ERROR = None


DIAG_EXIT_INVALID_REQUEST = 40
DIAG_EXIT_TIMEOUT = 41
DIAG_EXIT_BACKEND_ERROR = 42


@dataclass
class ParsedDiagRequest:
    original_text: str
    data: bytes
    hex_text: str
    preview: str


@dataclass
class DiagExecResult:
    exit_code: int
    log_path: Path
    result_path: Path
    payload: dict[str, Any]


def _require_serial() -> None:
    if serial is None:
        raise RuntimeError(f"pyserial is required for diag UART features: {SERIAL_IMPORT_ERROR}")


def diag_exec_supported() -> bool:
    return serial is not None or _powershell_available()


def _powershell_available() -> bool:
    return command_exists("powershell") or command_exists("powershell.exe")


def _unlink_if_exists(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except TypeError:
        if path.exists():
            path.unlink()


def _canonical_hex(data: bytes) -> str:
    return " ".join(f"{byte:02X}" for byte in data)


def _preview_text(text: str) -> str:
    rendered: list[str] = []
    for char in text:
        if char == "\r":
            rendered.append("\\r")
        elif char == "\n":
            rendered.append("\\n")
        elif char == "\t":
            rendered.append("\\t")
        elif char.isprintable():
            rendered.append(char)
        else:
            codepoint = ord(char)
            if codepoint <= 0xFF:
                rendered.append(f"\\x{codepoint:02X}")
            else:
                rendered.append(f"\\u{codepoint:04X}")
    return "".join(rendered)


def _preview_bytes(data: bytes, encoding: str) -> str:
    if not data:
        return ""
    try:
        decoded = data.decode(encoding, errors="replace")
    except LookupError:
        decoded = data.decode("utf-8", errors="replace")
    return _preview_text(decoded)


def parse_hex_request(text: str, encoding: str = "utf-8") -> ParsedDiagRequest:
    collapsed = "".join(char for char in str(text) if not char.isspace())
    if not collapsed:
        raise ValueError("hex request is empty")
    if len(collapsed) % 2 != 0:
        raise ValueError("hex request must contain an even number of hex digits")
    try:
        data = bytes.fromhex(collapsed)
    except ValueError as exc:
        raise ValueError("hex request contains non-hex characters") from exc
    return ParsedDiagRequest(
        original_text=str(text).strip(),
        data=data,
        hex_text=_canonical_hex(data),
        preview=_preview_bytes(data, encoding),
    )


def _load_script_requests(script_path: Path) -> list[str]:
    return [
        line.strip()
        for line in script_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _normalize_requests(cfg: dict, hex_requests: list[str], script_path: Path | None) -> list[ParsedDiagRequest]:
    diag_cfg = cfg.get("diag_uart", {})
    encoding = str(diag_cfg.get("encoding", "utf-8"))
    raw_requests = [str(item).strip() for item in hex_requests if str(item).strip()]
    if script_path is not None:
        raw_requests.extend(_load_script_requests(script_path))
    if not raw_requests:
        raw_requests = [str(item).strip() for item in diag_cfg.get("default_hex_requests", []) if str(item).strip()]
    if not raw_requests:
        raise ValueError("diag exec requires --hex, --script, or diag_uart.default_hex_requests")
    return [parse_hex_request(item, encoding) for item in raw_requests]


def _build_payload(
    cfg: dict,
    requests: list[ParsedDiagRequest],
    log_path: Path,
    result_path: Path,
    *,
    backend: str,
    exit_code: int,
    exchanges: list[dict[str, Any]],
    error: str = "",
) -> dict[str, Any]:
    diag_cfg = cfg.get("diag_uart", {})
    payload = {
        "generated_at": utc_now_iso(),
        "status": "ok" if exit_code == 0 else "error",
        "exit_code": int(exit_code),
        "backend": backend,
        "port": str(diag_cfg.get("port", "")),
        "baudrate": int(diag_cfg.get("baudrate", 0)),
        "encoding": str(diag_cfg.get("encoding", "utf-8")),
        "log_path": str(log_path),
        "result_path": str(result_path),
        "request_count": len(requests),
        "exchange_count": len(exchanges),
        "requests": [request.hex_text for request in requests],
        "exchanges": exchanges,
    }
    if error:
        payload["error"] = error
    return payload


def _finalize_result(
    cfg: dict,
    requests: list[ParsedDiagRequest],
    log_path: Path,
    result_path: Path,
    *,
    backend: str,
    exit_code: int,
    exchanges: list[dict[str, Any]],
    error: str = "",
) -> DiagExecResult:
    payload = _build_payload(
        cfg,
        requests,
        log_path,
        result_path,
        backend=backend,
        exit_code=exit_code,
        exchanges=exchanges,
        error=error,
    )
    write_json(result_path, payload)
    return DiagExecResult(
        exit_code=int(exit_code),
        log_path=log_path,
        result_path=result_path,
        payload=payload,
    )


def _write_backend_error(
    cfg: dict,
    requests: list[ParsedDiagRequest],
    log_path: Path,
    result_path: Path,
    *,
    backend: str,
    error: str,
    exit_code: int = DIAG_EXIT_BACKEND_ERROR,
    exchanges: list[dict[str, Any]] | None = None,
) -> DiagExecResult:
    ensure_dir(log_path.parent)
    log_path.write_text(
        f"[{utc_now_iso()}] [diag] start port={cfg.get('diag_uart', {}).get('port', '')} "
        f"baud={cfg.get('diag_uart', {}).get('baudrate', '')} backend={backend}\n"
        f"[{utc_now_iso()}] [diag] backend-error {error}\n"
        f"[{utc_now_iso()}] [diag] stop\n",
        encoding="utf-8",
    )
    return _finalize_result(
        cfg,
        requests,
        log_path,
        result_path,
        backend=backend,
        exit_code=exit_code,
        exchanges=exchanges or [],
        error=error,
    )


def _read_chunk(ser) -> bytes:
    waiting = getattr(ser, "in_waiting", 0)
    size = int(waiting) if isinstance(waiting, int) and waiting > 0 else 1
    raw = ser.read(size)
    return raw or b""


def _drain_startup(ser, duration_sec: float) -> bytes:
    drained = bytearray()
    end_time = time.time() + max(0.0, duration_sec)
    while time.time() < end_time:
        chunk = _read_chunk(ser)
        if chunk:
            drained.extend(chunk)
    return bytes(drained)


def _read_response(ser, first_byte_timeout_sec: float, idle_timeout_sec: float) -> tuple[bytes, bool]:
    response = bytearray()
    first_deadline = time.time() + max(0.0, first_byte_timeout_sec)
    while time.time() < first_deadline:
        chunk = _read_chunk(ser)
        if chunk:
            response.extend(chunk)
            break
    if not response:
        return b"", True

    idle_deadline = time.time() + max(0.0, idle_timeout_sec)
    while time.time() < idle_deadline:
        chunk = _read_chunk(ser)
        if chunk:
            response.extend(chunk)
            idle_deadline = time.time() + max(0.0, idle_timeout_sec)
    return bytes(response), False


def _request_payloads(requests: list[ParsedDiagRequest]) -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "hex_text": request.hex_text,
            "preview": request.preview,
            "data": [int(byte) for byte in request.data],
        }
        for index, request in enumerate(requests)
    ]


def _powershell_runtime_dir(cfg: dict) -> Path:
    return ensure_dir(Path(cfg["outputs"]["runtime_root_path"]) / "tmp")


def _powershell_exec_backend(
    cfg: dict,
    requests: list[ParsedDiagRequest],
    log_path: Path,
    result_path: Path,
) -> DiagExecResult:
    diag_cfg = cfg["diag_uart"]
    runtime_dir = _powershell_runtime_dir(cfg)
    request_path = runtime_dir / "diag_exec_requests.json"
    script_path = runtime_dir / "diag_exec_backend.ps1"
    request_path.write_text(json.dumps(_request_payloads(requests), ensure_ascii=False), encoding="utf-8")
    script_path.write_text(
        r"""
param(
  [string]$Port,
  [int]$Baudrate,
  [string]$LogPath,
  [string]$RequestFile,
  [string]$ResultFile,
  [string]$EncodingName,
  [int]$ReadTimeoutMs,
  [int]$StartupDrainMs,
  [int]$ResponseTimeoutMs,
  [int]$ResponseIdleTimeoutMs
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$requests = Get-Content -Raw -Path $RequestFile -Encoding UTF8 | ConvertFrom-Json
$serial = New-Object System.IO.Ports.SerialPort $Port, $Baudrate, ([System.IO.Ports.Parity]::None), 8, ([System.IO.Ports.StopBits]::One)
$serial.ReadTimeout = $ReadTimeoutMs
$serial.WriteTimeout = [Math]::Max($ReadTimeoutMs, 100)
$script:exitCode = 0
$script:errorText = ""
$script:exchanges = New-Object System.Collections.Generic.List[object]

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

function Write-Log([string]$line) {
  Append-Utf8 $LogPath $line
}

function Get-Decoding {
  try {
    return [System.Text.Encoding]::GetEncoding($EncodingName)
  } catch {
    return [System.Text.Encoding]::UTF8
  }
}

function Escape-Preview([string]$text) {
  $builder = New-Object System.Text.StringBuilder
  foreach ($char in $text.ToCharArray()) {
    $code = [int][char]$char
    if ($char -eq "`r") {
      [void]$builder.Append('\r')
    } elseif ($char -eq "`n") {
      [void]$builder.Append('\n')
    } elseif ($char -eq "`t") {
      [void]$builder.Append('\t')
    } elseif (-not [char]::IsControl($char)) {
      [void]$builder.Append($char)
    } elseif ($code -le 255) {
      [void]$builder.Append(('\x{0:X2}' -f $code))
    } else {
      [void]$builder.Append(('\u{0:X4}' -f $code))
    }
  }
  return $builder.ToString()
}

function Bytes-ToHex([byte[]]$bytes) {
  if (-not $bytes -or $bytes.Length -eq 0) {
    return ""
  }
  $parts = foreach ($byte in $bytes) { '{0:X2}' -f [int]$byte }
  return [string]::Join(' ', $parts)
}

function Bytes-ToPreview([byte[]]$bytes) {
  if (-not $bytes -or $bytes.Length -eq 0) {
    return ""
  }
  return Escape-Preview((Get-Decoding).GetString($bytes))
}

function Read-AvailableBytes {
  $buffer = New-Object System.Collections.Generic.List[byte]
  while ($serial.BytesToRead -gt 0) {
    $chunk = New-Object byte[] $serial.BytesToRead
    $read = $serial.Read($chunk, 0, $chunk.Length)
    for ($index = 0; $index -lt $read; $index++) {
      $buffer.Add([byte]$chunk[$index])
    }
  }
  return [byte[]]$buffer.ToArray()
}

function Read-ChunkSafe {
  try {
    if ($serial.BytesToRead -gt 0) {
      return Read-AvailableBytes
    }
    $firstByte = $serial.ReadByte()
    if ($firstByte -lt 0) {
      return [byte[]]@()
    }
    $buffer = New-Object System.Collections.Generic.List[byte]
    $buffer.Add([byte]$firstByte)
    foreach ($extraByte in (Read-AvailableBytes)) {
      $buffer.Add([byte]$extraByte)
    }
    return [byte[]]$buffer.ToArray()
  } catch [System.TimeoutException] {
    return [byte[]]@()
  }
}

function Drain-Startup([int]$durationMs) {
  if ($durationMs -le 0) {
    return [byte[]]@()
  }
  $buffer = New-Object System.Collections.Generic.List[byte]
  $deadline = [DateTime]::UtcNow.AddMilliseconds($durationMs)
  while ([DateTime]::UtcNow -lt $deadline) {
    $chunk = Read-ChunkSafe
    foreach ($byte in $chunk) {
      $buffer.Add([byte]$byte)
    }
  }
  return [byte[]]$buffer.ToArray()
}

function Read-Response([int]$firstByteTimeoutMs, [int]$idleTimeoutMs) {
  $buffer = New-Object System.Collections.Generic.List[byte]
  $firstDeadline = [DateTime]::UtcNow.AddMilliseconds($firstByteTimeoutMs)
  while ([DateTime]::UtcNow -lt $firstDeadline) {
    $chunk = Read-ChunkSafe
    if ($chunk.Length -gt 0) {
      foreach ($byte in $chunk) {
        $buffer.Add([byte]$byte)
      }
      break
    }
  }
  if ($buffer.Count -eq 0) {
    return @{ bytes = [byte[]]@(); timed_out = $true }
  }

  $idleDeadline = [DateTime]::UtcNow.AddMilliseconds($idleTimeoutMs)
  while ([DateTime]::UtcNow -lt $idleDeadline) {
    $chunk = Read-ChunkSafe
    if ($chunk.Length -gt 0) {
      foreach ($byte in $chunk) {
        $buffer.Add([byte]$byte)
      }
      $idleDeadline = [DateTime]::UtcNow.AddMilliseconds($idleTimeoutMs)
    }
  }
  return @{ bytes = [byte[]]$buffer.ToArray(); timed_out = $false }
}

function To-ByteArray($data) {
  $buffer = New-Object byte[] $data.Count
  for ($index = 0; $index -lt $data.Count; $index++) {
    $buffer[$index] = [byte]$data[$index]
  }
  return $buffer
}

try {
  Write-Log ("[{0}] [diag] start port={1} baud={2} backend=powershell" -f (Get-Timestamp), $Port, $Baudrate)
  $serial.Open()
  $serial.DiscardInBuffer()
  $serial.DiscardOutBuffer()

  $drained = Drain-Startup $StartupDrainMs
  if ($drained.Length -gt 0) {
    Write-Log ("[{0}] [diag] startup-drain hex={1} preview={2}" -f (Get-Timestamp), (Bytes-ToHex $drained), (Bytes-ToPreview $drained))
  }

  foreach ($request in $requests) {
    $requestBytes = To-ByteArray $request.data
    Write-Log ("[{0}] > index={1} hex={2} preview={3}" -f (Get-Timestamp), $request.index, $request.hex_text, $request.preview)
    $serial.Write($requestBytes, 0, $requestBytes.Length)

    $response = Read-Response $ResponseTimeoutMs $ResponseIdleTimeoutMs
    $responseBytes = [byte[]]$response.bytes
    $timedOut = [bool]$response.timed_out
    $responseHex = Bytes-ToHex $responseBytes
    $responsePreview = Bytes-ToPreview $responseBytes
    $exchangeStatus = if ($timedOut) { "timeout" } else { "ok" }
    if ($timedOut) {
      Write-Log ("[{0}] < index={1} [timeout]" -f (Get-Timestamp), $request.index)
      $script:exitCode = 41
    } else {
      Write-Log ("[{0}] < index={1} hex={2} preview={3}" -f (Get-Timestamp), $request.index, $responseHex, $responsePreview)
    }

    $script:exchanges.Add([ordered]@{
      index = [int]$request.index
      request_hex = [string]$request.hex_text
      request_preview = [string]$request.preview
      response_hex = [string]$responseHex
      response_preview = [string]$responsePreview
      response_size = [int]$responseBytes.Length
      timed_out = [bool]$timedOut
      status = [string]$exchangeStatus
    })

    if ($timedOut) {
      break
    }
  }
} catch {
  $script:errorText = $_.Exception.Message
  if ($script:exitCode -eq 0) {
    $script:exitCode = 42
  }
  Write-Log ("[{0}] [diag] backend-error {1}" -f (Get-Timestamp), $script:errorText)
} finally {
  if ($serial.IsOpen) {
    $serial.Close()
  }
  Write-Log ("[{0}] [diag] stop" -f (Get-Timestamp))
}

$requestHexes = @()
foreach ($request in $requests) {
  $requestHexes += [string]$request.hex_text
}
$finalStatus = if ($script:exitCode -eq 0) { "ok" } else { "error" }
$exchangeArray = @($script:exchanges.ToArray())
$payload = [ordered]@{}
$payload["generated_at"] = Get-Timestamp
$payload["status"] = [string]$finalStatus
$payload["exit_code"] = [int]$script:exitCode
$payload["backend"] = "powershell"
$payload["port"] = [string]$Port
$payload["baudrate"] = [int]$Baudrate
$payload["encoding"] = [string]$EncodingName
$payload["log_path"] = [string]$LogPath
$payload["result_path"] = [string]$ResultFile
$payload["request_count"] = [int]$requests.Count
$payload["exchange_count"] = [int]$script:exchanges.Count
$payload["requests"] = @($requestHexes)
$payload["exchanges"] = @($exchangeArray)
$payload["error"] = [string]$script:errorText
$payload | ConvertTo-Json -Depth 6 | Set-Content -Path $ResultFile -Encoding UTF8
""".strip()
        + "\n",
        encoding="utf-8",
    )
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
            "-LogPath",
            str(log_path),
            "-RequestFile",
            str(request_path),
            "-ResultFile",
            str(result_path),
            "-EncodingName",
            str(diag_cfg.get("encoding", "utf-8")),
            "-ReadTimeoutMs",
            str(max(20, int(float(diag_cfg.get("read_timeout_sec", 0.05)) * 1000))),
            "-StartupDrainMs",
            str(max(0, int(float(diag_cfg.get("startup_drain_sec", 0.0)) * 1000))),
            "-ResponseTimeoutMs",
            str(max(50, int(float(diag_cfg.get("response_timeout_sec", 1.0)) * 1000))),
            "-ResponseIdleTimeoutMs",
            str(max(20, int(float(diag_cfg.get("response_idle_timeout_sec", 0.1)) * 1000))),
        ],
        check=False,
        cwd=str(cfg["project_root_path"]),
        capture_output=True,
        text=True,
    )
    if (completed.returncode != 0) and (not result_path.exists()):
        raise RuntimeError(
            "PowerShell diag backend failed before producing a result file: "
            f"returncode={completed.returncode} stderr={completed.stderr.strip()}"
        )
    if not result_path.exists():
        raise RuntimeError(
            "PowerShell diag backend did not produce a result file: "
            f"returncode={completed.returncode} stderr={completed.stderr.strip()}"
        )
    payload = json.loads(result_path.read_text(encoding="utf-8-sig"))
    return DiagExecResult(
        exit_code=int(payload.get("exit_code", 1)),
        log_path=log_path,
        result_path=result_path,
        payload=payload,
    )


def execute_diag_requests(
    cfg: dict,
    hex_requests: list[str],
    log_path: Path,
    result_path: Path,
    *,
    script_path: Path | None = None,
) -> DiagExecResult:
    ensure_dir(log_path.parent)
    ensure_dir(result_path.parent)
    _unlink_if_exists(log_path)
    _unlink_if_exists(result_path)

    if not cfg.get("diag_uart", {}).get("enabled", True):
        return _write_backend_error(
            cfg,
            [],
            log_path,
            result_path,
            backend="disabled",
            error="diag_uart is disabled by config",
        )

    try:
        requests = _normalize_requests(cfg, hex_requests, script_path)
    except Exception as exc:
        return _write_backend_error(
            cfg,
            [],
            log_path,
            result_path,
            backend="validation",
            error=str(exc),
            exit_code=DIAG_EXIT_INVALID_REQUEST,
        )

    if serial is None:
        if not _powershell_available():
            return _write_backend_error(
                cfg,
                requests,
                log_path,
                result_path,
                backend="unavailable",
                error=(
                    f"pyserial unavailable: {SERIAL_IMPORT_ERROR}. "
                    "PowerShell fallback is not available in the current environment."
                ),
            )
        try:
            return _powershell_exec_backend(cfg, requests, log_path, result_path)
        except Exception as exc:
            return _write_backend_error(
                cfg,
                requests,
                log_path,
                result_path,
                backend="powershell",
                error=str(exc),
            )

    diag_cfg = cfg["diag_uart"]
    exchanges: list[dict[str, Any]] = []
    with log_path.open("w", encoding="utf-8") as fp:
        fp.write(
            f"[{utc_now_iso()}] [diag] start port={diag_cfg['port']} "
            f"baud={diag_cfg['baudrate']} backend=pyserial\n"
        )
        fp.flush()
        try:
            with serial.Serial(
                diag_cfg["port"],
                int(diag_cfg["baudrate"]),
                timeout=float(diag_cfg.get("read_timeout_sec", 0.05)),
            ) as ser:
                for method_name in ("reset_input_buffer", "reset_output_buffer"):
                    method = getattr(ser, method_name, None)
                    if callable(method):
                        method()

                drained = _drain_startup(ser, float(diag_cfg.get("startup_drain_sec", 0.0)))
                if drained:
                    fp.write(
                        f"[{utc_now_iso()}] [diag] startup-drain hex={_canonical_hex(drained)} "
                        f"preview={_preview_bytes(drained, str(diag_cfg.get('encoding', 'utf-8')))}\n"
                    )

                for index, request in enumerate(requests):
                    fp.write(f"[{utc_now_iso()}] > index={index} hex={request.hex_text} preview={request.preview}\n")
                    ser.write(request.data)
                    ser.flush()

                    response, timed_out = _read_response(
                        ser,
                        float(diag_cfg.get("response_timeout_sec", 1.0)),
                        float(diag_cfg.get("response_idle_timeout_sec", 0.1)),
                    )
                    response_hex = _canonical_hex(response)
                    response_preview = _preview_bytes(response, str(diag_cfg.get("encoding", "utf-8")))
                    exchange = {
                        "index": index,
                        "request_hex": request.hex_text,
                        "request_preview": request.preview,
                        "response_hex": response_hex,
                        "response_preview": response_preview,
                        "response_size": len(response),
                        "timed_out": bool(timed_out),
                        "status": "timeout" if timed_out else "ok",
                    }
                    exchanges.append(exchange)

                    if timed_out:
                        fp.write(f"[{utc_now_iso()}] < index={index} [timeout]\n")
                        fp.write(f"[{utc_now_iso()}] [diag] stop\n")
                        fp.flush()
                        return _finalize_result(
                            cfg,
                            requests,
                            log_path,
                            result_path,
                            backend="pyserial",
                            exit_code=DIAG_EXIT_TIMEOUT,
                            exchanges=exchanges,
                        )

                    fp.write(
                        f"[{utc_now_iso()}] < index={index} hex={response_hex} preview={response_preview}\n"
                    )
                fp.write(f"[{utc_now_iso()}] [diag] stop\n")
        except Exception as exc:
            fp.write(f"[{utc_now_iso()}] [diag] backend-error {exc}\n")
            fp.write(f"[{utc_now_iso()}] [diag] stop\n")
            fp.flush()
            return _finalize_result(
                cfg,
                requests,
                log_path,
                result_path,
                backend="pyserial",
                exit_code=DIAG_EXIT_BACKEND_ERROR,
                exchanges=exchanges,
                error=str(exc),
            )

    return _finalize_result(
        cfg,
        requests,
        log_path,
        result_path,
        backend="pyserial",
        exit_code=0,
        exchanges=exchanges,
    )
