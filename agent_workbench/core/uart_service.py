from __future__ import annotations

import json
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cli_diag_service import collect_cli_diag
from .flash_service import run_reset
from .utils import (
    clear_pid_file,
    command_exists,
    ensure_dir,
    is_process_alive,
    read_pid,
    render_template,
    spawn_detached_python,
    terminate_process,
    utc_now_iso,
    write_pid,
)

try:
    import serial  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - env specific
    serial = None
    SERIAL_IMPORT_ERROR = exc
else:
    SERIAL_IMPORT_ERROR = None


@dataclass
class UartExecResult:
    exit_code: int
    transcript_lines: list[str]
    saw_ready: bool
    saw_prompt: bool
    timeout_commands: list[str]
    diag_path: Path | None = None
    diag: dict[str, Any] | None = None


def _require_serial() -> None:
    if serial is None:
        raise RuntimeError(f"pyserial is required for UART features: {SERIAL_IMPORT_ERROR}")


def uart_exec_supported() -> bool:
    return serial is not None or _powershell_available()


def uart_logger_supported() -> bool:
    return serial is not None or _powershell_available()


def _decode_line(raw: bytes, encoding: str) -> str:
    return raw.decode(encoding, errors="replace").rstrip("\r\n")


def _prompt_matches(text: str, prompt: str) -> bool:
    return prompt.strip() != "" and text.strip() == prompt.strip()


def _write_rx(fp, transcript_lines: list[str], text: str) -> None:
    transcript_lines.append(text)
    fp.write(f"[{utc_now_iso()}] < {text}\n")


def _read_chunk(ser, encoding: str) -> str:
    waiting = getattr(ser, "in_waiting", 0)
    size = int(waiting) if isinstance(waiting, int) and waiting > 0 else 1
    raw = ser.read(size)
    if not raw:
        return ""
    return raw.decode(encoding, errors="replace")


def _consume_text_buffer(buffer: str, text: str, prompt: str) -> tuple[list[str], str, int]:
    lines: list[str] = []
    prompt_hits = 0
    pending = buffer + text
    normalized_prompt = prompt.strip()

    while pending:
        newline_index = pending.find("\n")
        prompt_index = pending.find(prompt) if prompt else -1

        if prompt_index >= 0 and (newline_index < 0 or prompt_index < newline_index):
            prefix = pending[:prompt_index].rstrip("\r")
            if prefix.strip() != "":
                lines.append(prefix)

            prompt_end = prompt_index + len(prompt)
            while prompt_end < len(pending) and pending[prompt_end] == " ":
                prompt_end += 1

            lines.append(normalized_prompt or prompt)
            prompt_hits += 1
            pending = pending[prompt_end:]
            continue

        if newline_index < 0:
            break

        line = pending[:newline_index].rstrip("\r")
        pending = pending[newline_index + 1 :]
        if line != "":
            lines.append(line)

    return lines, pending, prompt_hits


def _flush_pending_text(buffer: str) -> list[str]:
    tail = buffer.rstrip("\r\n")
    if tail.strip() == "":
        return []
    return [tail]


def _drain_startup(ser, encoding: str, timeout_sec: float, prompt: str) -> list[str]:
    lines: list[str] = []
    pending = ""
    end_time = time.time() + timeout_sec
    while time.time() < end_time:
        text = _read_chunk(ser, encoding)
        if text:
            chunk_lines, pending, _ = _consume_text_buffer(pending, text, prompt)
            lines.extend(chunk_lines)
    lines.extend(_flush_pending_text(pending))
    return lines


def _wait_for_ready(ser, encoding: str, timeout_sec: float, ready_banner: str, prompt: str) -> tuple[list[str], bool, bool]:
    lines: list[str] = []
    saw_ready = False
    saw_prompt = False
    pending = ""
    end_time = time.time() + timeout_sec
    while time.time() < end_time:
        text = _read_chunk(ser, encoding)
        if not text:
            continue
        chunk_lines, pending, _ = _consume_text_buffer(pending, text, prompt)
        for line in chunk_lines:
            lines.append(line)
            if ready_banner and ready_banner in line:
                saw_ready = True
            if _prompt_matches(line, prompt):
                saw_prompt = True
        if saw_ready and saw_prompt:
            break
    for line in _flush_pending_text(pending):
        lines.append(line)
        if ready_banner and ready_banner in line:
            saw_ready = True
        if _prompt_matches(line, prompt):
            saw_prompt = True
    return lines, saw_ready, saw_prompt


def _wait_for_command_response(ser, encoding: str, timeout_sec: float, prompt: str) -> tuple[list[str], bool]:
    lines: list[str] = []
    saw_prompt = False
    pending = ""
    end_time = time.time() + timeout_sec
    while time.time() < end_time:
        text = _read_chunk(ser, encoding)
        if not text:
            continue
        chunk_lines, pending, _ = _consume_text_buffer(pending, text, prompt)
        for line in chunk_lines:
            lines.append(line)
            if _prompt_matches(line, prompt):
                saw_prompt = True
                break
        if saw_prompt:
            break
    if not saw_prompt:
        lines.extend(_flush_pending_text(pending))
    return lines, saw_prompt


def _powershell_available() -> bool:
    return command_exists("powershell") or command_exists("powershell.exe")


def _powershell_runtime_dir(cfg: dict) -> Path:
    return ensure_dir(cfg["outputs"]["runtime_root_path"] / "tmp")


def _render_reset_command(cfg: dict) -> str:
    flash_method = cfg["tools"]["flash"].get("default_method", "stlink_cli")
    flash_cfg = cfg["tools"]["flash"].get("methods", {}).get(flash_method, {})
    return render_template(flash_cfg.get("reset", ""), cfg.get("template_values", {}))


def _powershell_exec_backend(
    cfg: dict,
    commands: list[str],
    transcript_path: Path,
    *,
    reset_first: bool,
    require_ready: bool,
    ready_banner: str,
    prompt: str,
    startup_drain_sec: float,
    line_timeout_sec: float,
    ready_timeout_sec: float,
    command_timeout_sec: float,
) -> UartExecResult:
    runtime_dir = _powershell_runtime_dir(cfg)
    commands_path = runtime_dir / "uart_exec_commands.json"
    result_path = runtime_dir / "uart_exec_result.json"
    script_path = runtime_dir / "uart_exec_backend.ps1"
    try:
        result_path.unlink(missing_ok=True)
    except TypeError:
        if result_path.exists():
            result_path.unlink()
    commands_path.write_text(json.dumps(commands, ensure_ascii=False), encoding="utf-8")
    script_path.write_text(
        r"""
param(
  [string]$Port,
  [int]$Baudrate,
  [string]$TranscriptPath,
  [string]$CommandFile,
  [string]$ResultFile,
  [string]$ResetCommand,
  [string]$ReadyBanner,
  [string]$Prompt,
  [int]$ReadTimeoutMs,
  [int]$StartupDrainMs,
  [int]$ReadyTimeoutMs,
  [int]$CommandTimeoutMs,
  [int]$RequireReady,
  [int]$ResetFirst
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$commands = Get-Content -Raw -Path $CommandFile -Encoding UTF8 | ConvertFrom-Json
$serial = New-Object System.IO.Ports.SerialPort $Port, $Baudrate, ([System.IO.Ports.Parity]::None), 8, ([System.IO.Ports.StopBits]::One)
$serial.Encoding = [System.Text.Encoding]::UTF8
$serial.NewLine = "`n"
$serial.ReadTimeout = $ReadTimeoutMs
$transcript = New-Object System.Collections.Generic.List[string]
$timeoutCommands = New-Object System.Collections.Generic.List[string]
$script:exitCode = 0
$script:sawReady = $false
$script:sawPrompt = $false
$script:promptCount = 0
$script:pendingText = ""

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

function Write-TranscriptLine([string]$line) {
  Append-Utf8 $TranscriptPath $line
}

function Add-Rx([string]$text) {
  $transcript.Add($text)
  Write-TranscriptLine ("[{0}] < {1}" -f (Get-Timestamp), $text)
  if ($ReadyBanner -and $text.Contains($ReadyBanner)) {
    $script:sawReady = $true
  }
  if ($Prompt -and $text.Trim() -eq $Prompt.Trim()) {
    $script:sawPrompt = $true
    $script:promptCount += 1
  }
}

function Read-ChunkSafe {
  try {
    if ($serial.BytesToRead -gt 0) {
      $text = $serial.ReadExisting()
      if (-not [string]::IsNullOrEmpty($text)) {
        return $text
      }
    }
    $charCode = $serial.ReadChar()
    if ($charCode -ge 0) {
      return [string][char]$charCode
    }
  } catch [System.TimeoutException] {
    return $null
  }
}

function Flush-PendingText {
  $tail = $script:pendingText.TrimEnd("`r", "`n")
  if (-not [string]::IsNullOrWhiteSpace($tail)) {
    Add-Rx $tail
  }
  $script:pendingText = ""
}

function Process-PendingText {
  while ($true) {
    $newlineIndex = $script:pendingText.IndexOf("`n")
    $promptIndex = if ([string]::IsNullOrEmpty($Prompt)) { -1 } else { $script:pendingText.IndexOf($Prompt) }

    if (($promptIndex -ge 0) -and (($newlineIndex -lt 0) -or ($promptIndex -lt $newlineIndex))) {
      $prefix = $script:pendingText.Substring(0, $promptIndex).TrimEnd("`r")
      if (-not [string]::IsNullOrWhiteSpace($prefix)) {
        Add-Rx $prefix
      }
      $promptEnd = $promptIndex + $Prompt.Length
      while (($promptEnd -lt $script:pendingText.Length) -and ($script:pendingText[$promptEnd] -eq ' ')) {
        $promptEnd += 1
      }
      Add-Rx $Prompt.Trim()
      $script:pendingText = $script:pendingText.Substring($promptEnd)
      continue
    }

    if ($newlineIndex -lt 0) {
      break
    }

    $line = $script:pendingText.Substring(0, $newlineIndex).TrimEnd("`r")
    $script:pendingText = $script:pendingText.Substring($newlineIndex + 1)
    if ($line.Length -gt 0) {
      Add-Rx $line
    }
  }
}

function Pump-Serial {
  $chunk = Read-ChunkSafe
  if ([string]::IsNullOrEmpty($chunk)) {
    return $false
  }
  $script:pendingText += $chunk
  Process-PendingText
  return $true
}

function Drain-ForMs([int]$durationMs) {
  if ($durationMs -le 0) {
    return
  }
  $deadline = [DateTime]::UtcNow.AddMilliseconds($durationMs)
  while ([DateTime]::UtcNow -lt $deadline) {
    [void](Pump-Serial)
  }
  Flush-PendingText
}

function Invoke-ResetCommand {
  if ([string]::IsNullOrWhiteSpace($ResetCommand)) {
    return 0
  }
  $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/d", "/c", $ResetCommand -Wait -NoNewWindow -PassThru
  return [int]$proc.ExitCode
}

function Wait-Ready {
  $deadline = [DateTime]::UtcNow.AddMilliseconds($ReadyTimeoutMs)
  while ([DateTime]::UtcNow -lt $deadline) {
    [void](Pump-Serial)
    if ($script:sawReady -and $script:sawPrompt) {
      return
    }
  }
  Flush-PendingText
  if (-not $script:sawReady) {
    $script:exitCode = 31
    Write-TranscriptLine ("[{0}] [cli] ready-missing expected={1}" -f (Get-Timestamp), $ReadyBanner)
  } elseif (-not $script:sawPrompt) {
    $script:exitCode = 32
    Write-TranscriptLine ("[{0}] [cli] prompt-missing expected={1}" -f (Get-Timestamp), $Prompt)
  }
}

function Run-CommandLoop {
  foreach ($command in $commands) {
    Write-TranscriptLine ("[{0}] > {1}" -f (Get-Timestamp), $command)
    $serial.Write($command + "`r`n")
    $deadline = [DateTime]::UtcNow.AddMilliseconds($CommandTimeoutMs)
    $startPromptCount = $script:promptCount
    $hadAnyData = $false
    while ([DateTime]::UtcNow -lt $deadline) {
      if (Pump-Serial) {
        $hadAnyData = $true
      }
      if ($script:promptCount -gt $startPromptCount) {
        break
      }
    }
    Flush-PendingText
    if (-not $hadAnyData) {
      $timeoutCommands.Add($command)
      Write-TranscriptLine ("[{0}] < [timeout]" -f (Get-Timestamp))
      $script:exitCode = 33
      return
    }
    if ($script:promptCount -le $startPromptCount) {
      $timeoutCommands.Add($command)
      Write-TranscriptLine ("[{0}] [cli] prompt-missing-after-command command={1}" -f (Get-Timestamp), $command)
      $script:exitCode = 34
      return
    }
  }
}

try {
  $serial.Open()
  $serial.DiscardInBuffer()
  $serial.DiscardOutBuffer()
  Write-TranscriptLine ("[{0}] [cli] start port={1} baud={2} expect_ready={3} reset_first={4} backend=powershell" -f (Get-Timestamp), $Port, $Baudrate, $RequireReady, $ResetFirst)
  Drain-ForMs $StartupDrainMs
  if ($ResetFirst -eq 1) {
    $script:sawReady = $false
    $script:sawPrompt = $false
    $script:promptCount = 0
    $script:pendingText = ""
    $resetExit = Invoke-ResetCommand
    Write-TranscriptLine ("[{0}] [cli] reset-first exit={1}" -f (Get-Timestamp), $resetExit)
    if ($resetExit -ne 0) {
      $script:exitCode = if ($resetExit -eq 0) { 30 } else { [int]$resetExit }
    }
  }
  if (($script:exitCode -eq 0) -and ($RequireReady -eq 1)) {
    Wait-Ready
  }
  if ($script:exitCode -eq 0) {
    Run-CommandLoop
  }
} finally {
  if ($serial.IsOpen) {
    $serial.Close()
  }
  Write-TranscriptLine ("[{0}] [cli] stop" -f (Get-Timestamp))
}

[ordered]@{
  exit_code = $script:exitCode
  transcript_lines = @($transcript)
  saw_ready = $script:sawReady
  saw_prompt = $script:sawPrompt
  timeout_commands = @($timeoutCommands)
} | ConvertTo-Json -Depth 4 | Set-Content -Path $ResultFile -Encoding UTF8
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
            str(cfg["uart"]["port"]),
            "-Baudrate",
            str(int(cfg["uart"]["baudrate"])),
            "-TranscriptPath",
            str(transcript_path),
            "-CommandFile",
            str(commands_path),
            "-ResultFile",
            str(result_path),
            "-ResetCommand",
            _render_reset_command(cfg) if reset_first else "",
            "-ReadyBanner",
            ready_banner,
            "-Prompt",
            prompt,
            "-ReadTimeoutMs",
            str(max(50, int(line_timeout_sec * 1000))),
            "-StartupDrainMs",
            str(max(0, int(startup_drain_sec * 1000))),
            "-ReadyTimeoutMs",
            str(max(100, int(ready_timeout_sec * 1000))),
            "-CommandTimeoutMs",
            str(max(100, int(command_timeout_sec * 1000))),
            "-RequireReady",
            str(1 if require_ready else 0),
            "-ResetFirst",
            str(1 if reset_first else 0),
        ],
        check=False,
        cwd=str(cfg["project_root_path"]),
        capture_output=True,
        text=True,
    )
    if (completed.returncode != 0) and (not result_path.exists()):
        raise RuntimeError(
            "PowerShell UART backend failed before producing a result file: "
            f"returncode={completed.returncode} stderr={completed.stderr.strip()}"
        )
    if not result_path.exists():
        raise RuntimeError(
            "PowerShell UART backend did not produce a result file: "
            f"returncode={completed.returncode} stderr={completed.stderr.strip()}"
        )
    payload = json.loads(result_path.read_text(encoding="utf-8-sig"))
    return UartExecResult(
        exit_code=int(payload.get("exit_code", 1)),
        transcript_lines=list(payload.get("transcript_lines", [])),
        saw_ready=bool(payload.get("saw_ready", False)),
        saw_prompt=bool(payload.get("saw_prompt", False)),
        timeout_commands=list(payload.get("timeout_commands", [])),
    )


def _powershell_logger_backend(
    port: str,
    baudrate: int,
    encoding: str,
    timeout_sec: float,
    log_path: Path,
    stop_event: threading.Event,
) -> int:
    runtime_dir = ensure_dir(log_path.parent.parent / "tmp")
    script_path = runtime_dir / "uart_logger_backend.ps1"
    script_path.write_text(
        r"""
param(
  [string]$Port,
  [int]$Baudrate,
  [string]$LogPath,
  [int]$ReadTimeoutMs
)
$ErrorActionPreference = "Stop"
$serial = New-Object System.IO.Ports.SerialPort $Port, $Baudrate, ([System.IO.Ports.Parity]::None), 8, ([System.IO.Ports.StopBits]::One)
$serial.Encoding = [System.Text.Encoding]::UTF8
$serial.NewLine = "`n"
$serial.ReadTimeout = $ReadTimeoutMs
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
try {
  $serial.Open()
  Append-Utf8 $LogPath ("[{0}] [uart] start port={1} baud={2} backend=powershell" -f (Get-Timestamp), $Port, $Baudrate)
  while ($true) {
    try {
      $line = $serial.ReadLine().TrimEnd("`r", "`n")
      Append-Utf8 $LogPath ("[{0}] {1}" -f (Get-Timestamp), $line)
    } catch [System.TimeoutException] {
      continue
    }
  }
} finally {
  if ($serial.IsOpen) {
    $serial.Close()
  }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-Port",
            str(port),
            "-Baudrate",
            str(baudrate),
            "-LogPath",
            str(log_path),
            "-ReadTimeoutMs",
            str(max(50, int(timeout_sec * 1000))),
        ],
        cwd=str(log_path.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        while not stop_event.is_set():
            time.sleep(0.1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5.0)
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(f"[{utc_now_iso()}] [uart] stop\n")
    return 0


class UartLogger:
    def __init__(self, port: str, baudrate: int, encoding: str, timeout_sec: float, log_path: Path):
        self.port = port
        self.baudrate = baudrate
        self.encoding = encoding
        self.timeout_sec = timeout_sec
        self.log_path = log_path
        self.stop_event = threading.Event()

    def run(self, echo_stdout: bool = False) -> int:
        if serial is None:
            if echo_stdout:
                raise RuntimeError("UART console echo requires pyserial; PowerShell fallback supports log capture only.")
            if not _powershell_available():
                _require_serial()
            ensure_dir(self.log_path.parent)
            return _powershell_logger_backend(
                self.port,
                self.baudrate,
                self.encoding,
                self.timeout_sec,
                self.log_path,
                self.stop_event,
            )
        ensure_dir(self.log_path.parent)
        with serial.Serial(self.port, self.baudrate, timeout=self.timeout_sec) as ser:
            with self.log_path.open("a", encoding="utf-8") as fp:
                fp.write(f"[{utc_now_iso()}] [uart] start port={self.port} baud={self.baudrate}\n")
                while not self.stop_event.is_set():
                    raw = ser.readline()
                    if not raw:
                        continue
                    text = _decode_line(raw, self.encoding)
                    line = f"[{utc_now_iso()}] {text}\n"
                    fp.write(line)
                    fp.flush()
                    if echo_stdout:
                        print(line, end="")
                fp.write(f"[{utc_now_iso()}] [uart] stop\n")
        return 0


def _print_help_rows(help_rows: list[dict]) -> None:
    print("COMMAND              DESCRIPTION | USAGE | PARAMS")
    print("-------------------  -----------------------------------------------")
    for row in help_rows:
        print(f"{row.get('command', ''):<19}  {row.get('detail', '')}")
    print(":help                local console help")
    print(":quit                quit console")


def run_uart_console(cfg: dict, log_path: Path) -> int:
    _require_serial()
    uart = cfg["uart"]
    ensure_dir(log_path.parent)
    stop_event = threading.Event()
    with serial.Serial(
        uart["port"],
        int(uart["baudrate"]),
        timeout=float(uart.get("line_timeout_sec", 0.2)),
    ) as ser, log_path.open("a", encoding="utf-8") as fp:
        fp.write(f"[{utc_now_iso()}] [uart-console] start port={uart['port']} baud={uart['baudrate']}\n")

        def reader() -> None:
            while not stop_event.is_set():
                raw = ser.readline()
                if not raw:
                    continue
                text = _decode_line(raw, uart.get("encoding", "utf-8"))
                line = f"[{utc_now_iso()}] {text}\n"
                fp.write(line)
                fp.flush()
                print(line, end="")

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        time.sleep(0.15)
        _print_help_rows(uart.get("help_rows", []))
        print("")
        print("UART console is running. Type board command and press Enter.")
        try:
            while True:
                line = input("> ")
                if not line:
                    continue
                command = line.strip()
                if command == ":quit":
                    break
                if command == ":help":
                    _print_help_rows(uart.get("help_rows", []))
                    continue
                ser.write((line + "\r\n").encode(uart.get("encoding", "utf-8"), errors="ignore"))
        except KeyboardInterrupt:
            pass
        finally:
            stop_event.set()
            thread.join(timeout=2.0)
            fp.write(f"[{utc_now_iso()}] [uart-console] stop\n")
    return 0


def execute_uart_commands(
    cfg: dict,
    commands: list[str],
    transcript_path: Path,
    *,
    reset_first: bool = False,
    expect_ready: bool | None = None,
    diag_path: Path | None = None,
    reset_log_path: Path | None = None,
) -> UartExecResult:
    uart = cfg["uart"]
    encoding = uart.get("encoding", "utf-8")
    line_timeout_sec = float(uart.get("line_timeout_sec", 0.2))
    startup_drain_sec = float(uart.get("startup_drain_sec", 0.5))
    command_timeout_sec = float(uart.get("command_timeout_sec", 2.0))
    ready_timeout_sec = float(uart.get("ready_timeout_sec", max(3.0, command_timeout_sec)))
    ready_banner = str(uart.get("ready_banner", "cli ready"))
    prompt = str(uart.get("prompt", "cli>"))
    require_ready = bool(uart.get("exec_require_ready", True)) if expect_ready is None else bool(expect_ready)
    fail_on_timeout = bool(uart.get("exec_fail_on_timeout", True))
    transcript_lines: list[str] = []
    timeout_commands: list[str] = []
    saw_ready = False
    saw_prompt = False
    exit_code = 0

    ensure_dir(transcript_path.parent)
    diag_target = diag_path or transcript_path.with_name("cli_diag.json")
    reset_target = reset_log_path or (cfg["outputs"]["runtime_root_path"] / "uart_exec_reset.log")
    try:
        diag_target.unlink(missing_ok=True)
    except TypeError:
        if diag_target.exists():
            diag_target.unlink()

    if serial is None:
        if not _powershell_available():
            _require_serial()
        ensure_dir(transcript_path.parent)
        try:
            transcript_path.unlink(missing_ok=True)
        except TypeError:
            if transcript_path.exists():
                transcript_path.unlink()
        try:
            result = _powershell_exec_backend(
                cfg,
                commands,
                transcript_path,
                reset_first=reset_first,
                require_ready=require_ready,
                ready_banner=ready_banner,
                prompt=prompt,
                startup_drain_sec=startup_drain_sec,
                line_timeout_sec=line_timeout_sec,
                ready_timeout_sec=ready_timeout_sec,
                command_timeout_sec=command_timeout_sec,
            )
        except RuntimeError as exc:
            message = str(exc).strip()
            transcript_path.write_text(
                f"[{utc_now_iso()}] [cli] start port={uart['port']} baud={uart['baudrate']} "
                f"expect_ready={int(require_ready)} reset_first={int(reset_first)} backend=powershell\n"
                f"[{utc_now_iso()}] [cli] backend-error {message}\n"
                f"[{utc_now_iso()}] [cli] stop\n",
                encoding="utf-8",
            )
            diag_result_path = collect_cli_diag(
                cfg,
                diag_target,
                saw_ready=False,
                saw_prompt=False,
                timeout_commands=[],
            )
            diag_payload = json.loads(diag_result_path.read_text(encoding="utf-8")) if diag_result_path.exists() else None
            return UartExecResult(
                exit_code=35,
                transcript_lines=[],
                saw_ready=False,
                saw_prompt=False,
                timeout_commands=[],
                diag_path=diag_result_path,
                diag=diag_payload,
            )
        if result.exit_code != 0:
            diag_result_path = collect_cli_diag(
                cfg,
                diag_target,
                saw_ready=result.saw_ready,
                saw_prompt=result.saw_prompt,
                timeout_commands=result.timeout_commands,
            )
            result.diag_path = diag_result_path
            if diag_result_path.exists():
                result.diag = json.loads(diag_result_path.read_text(encoding="utf-8"))
        return result

    with serial.Serial(
        uart["port"],
        int(uart["baudrate"]),
        timeout=line_timeout_sec,
    ) as ser, transcript_path.open("w", encoding="utf-8") as fp:
        fp.write(
            f"[{utc_now_iso()}] [cli] start port={uart['port']} baud={uart['baudrate']} "
            f"expect_ready={int(require_ready)} reset_first={int(reset_first)}\n"
        )
        for method_name in ("reset_input_buffer", "reset_output_buffer"):
            method = getattr(ser, method_name, None)
            if callable(method):
                method()

        if startup_drain_sec > 0:
            for line in _drain_startup(ser, encoding, startup_drain_sec, prompt):
                _write_rx(fp, transcript_lines, line)
                saw_ready = saw_ready or (ready_banner in line)
                saw_prompt = saw_prompt or _prompt_matches(line, prompt)

        if reset_first and exit_code == 0:
            fp.write(f"[{utc_now_iso()}] [cli] reset-first start\n")
            reset_code = run_reset(cfg, method=None, log_path=reset_target)
            fp.write(f"[{utc_now_iso()}] [cli] reset-first exit={reset_code}\n")
            saw_ready = False
            saw_prompt = False
            if reset_code != 0:
                exit_code = int(reset_code) or 30

        if exit_code == 0 and require_ready:
            ready_lines, ready_seen, prompt_seen = _wait_for_ready(
                ser,
                encoding,
                ready_timeout_sec,
                ready_banner,
                prompt,
            )
            for line in ready_lines:
                _write_rx(fp, transcript_lines, line)
            saw_ready = saw_ready or ready_seen
            saw_prompt = saw_prompt or prompt_seen
            if not saw_ready:
                exit_code = 31
                fp.write(f"[{utc_now_iso()}] [cli] ready-missing expected={ready_banner}\n")
            elif not saw_prompt:
                exit_code = 32
                fp.write(f"[{utc_now_iso()}] [cli] prompt-missing expected={prompt}\n")

        if exit_code == 0:
            for command in commands:
                fp.write(f"[{utc_now_iso()}] > {command}\n")
                ser.write((command + "\r\n").encode(encoding, errors="ignore"))
                ser.flush()
                response_lines, prompt_seen = _wait_for_command_response(ser, encoding, command_timeout_sec, prompt)
                if not response_lines:
                    timeout_commands.append(command)
                    fp.write(f"[{utc_now_iso()}] < [timeout]\n")
                    if fail_on_timeout:
                        exit_code = 33
                        break
                    continue
                for line in response_lines:
                    _write_rx(fp, transcript_lines, line)
                saw_prompt = saw_prompt or prompt_seen
                if not prompt_seen:
                    timeout_commands.append(command)
                    fp.write(f"[{utc_now_iso()}] [cli] prompt-missing-after-command command={command}\n")
                    if fail_on_timeout:
                        exit_code = 34
                        break

        fp.write(f"[{utc_now_iso()}] [cli] stop\n")

    diag_payload = None
    diag_result_path: Path | None = None
    if exit_code != 0:
        diag_result_path = collect_cli_diag(
            cfg,
            diag_target,
            saw_ready=saw_ready,
            saw_prompt=saw_prompt,
            timeout_commands=timeout_commands,
        )
        if diag_result_path.exists():
            diag_payload = json.loads(diag_result_path.read_text(encoding="utf-8"))

    return UartExecResult(
        exit_code=exit_code,
        transcript_lines=transcript_lines,
        saw_ready=saw_ready,
        saw_prompt=saw_prompt,
        timeout_commands=timeout_commands,
        diag_path=diag_result_path,
        diag=diag_payload,
    )


def _pid_path(cfg: dict) -> Path:
    return ensure_dir(cfg["outputs"]["runtime_root_path"] / "pids") / "uart.pid"


def start_uart_daemon(cfg: dict, config_path: Path, workbench_script: Path) -> str:
    pid_file = _pid_path(cfg)
    old_pid = read_pid(pid_file)
    if old_pid and is_process_alive(old_pid):
        return f"uart logger already running pid={old_pid}"
    if old_pid:
        clear_pid_file(pid_file)
    out_dir = ensure_dir(cfg["outputs"]["runtime_root_path"] / "uart_live")
    args = [
        str(workbench_script),
        "uart",
        "run",
        "--config",
        str(config_path),
        "--log-path",
        str(out_dir / "uart.log"),
    ]
    pid = spawn_detached_python(args, cwd=cfg["project_root_path"])
    write_pid(pid_file, pid)
    return f"uart logger started pid={pid}, log={out_dir / 'uart.log'}"


def stop_uart_daemon(cfg: dict) -> str:
    pid_file = _pid_path(cfg)
    pid = read_pid(pid_file)
    if not pid:
        return "uart logger not running"
    if not is_process_alive(pid):
        clear_pid_file(pid_file)
        return f"uart logger stale pid cleaned pid={pid}"
    terminate_process(pid)
    clear_pid_file(pid_file)
    return f"uart logger stopped pid={pid}"


def uart_status(cfg: dict) -> str:
    pid = read_pid(_pid_path(cfg))
    if not pid:
        return "uart status: stopped"
    return f"uart status: {'running' if is_process_alive(pid) else 'stale'} pid={pid}"
