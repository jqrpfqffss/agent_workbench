from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field


FREQUENCY_UNITS = {
    "hz": 1,
    "khz": 1_000,
    "mhz": 1_000_000,
    "千赫": 1_000,
    "兆赫": 1_000_000,
}

TIME_UNITS_TO_MS = {
    "ms": 1.0,
    "毫秒": 1.0,
    "s": 1_000.0,
    "秒": 1_000.0,
}

_FREQUENCY_RE = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>hz|khz|mhz|千赫|兆赫)", re.IGNORECASE)
_DUTY_RE = re.compile(r"(?P<value>\d{1,3})\s*%(?:\s*(?:占空比|duty))?", re.IGNORECASE)
_PERIOD_RE = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|s|毫秒|秒)", re.IGNORECASE)
_PIN_RE = re.compile(r"(?<![A-Za-z0-9])P(?P<port>[A-H])\s*(?P<index>\d{1,2})(?![A-Za-z0-9])", re.IGNORECASE)
_TIMER_RE = re.compile(r"(?<![A-Za-z0-9])TIM(?P<index>\d{1,2})(?![A-Za-z0-9])", re.IGNORECASE)
_BAUD_RE = re.compile(r"(?<!\d)(?P<value>9600|19200|38400|57600|115200|230400|460800|921600)(?!\d)")
_VOLTAGE_RE = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?:v|伏)\b", re.IGNORECASE)
_CLI_COMMAND_RES = [
    re.compile(
        r"(?:CLI\s*)?(?:命令|command)\s*(?:名|name)?\s*[:：]?\s*[\"'`“”‘’]?(?P<name>[a-z_][a-z0-9_]*)[\"'`“”‘’]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:添加|新增|增加|加入|create|add)\s*(?:一个|一条)?\s*(?:CLI\s*)?(?:命令|command)\s*[\"'`“”‘’]?(?P<name>[a-z_][a-z0-9_]*)[\"'`“”‘’]?",
        re.IGNORECASE,
    ),
]

_KEYWORD_GROUPS = {
    "pwm": ["pwm", "蜂鸣器", "方波", "占空比"],
    "timer": ["定时器", "timer", "周期", "中断"],
    "cli": ["cli", "命令", "串口", "command", "help", "status"],
    "gpio": ["gpio", "引脚", "led", "io"],
    "adc": ["adc", "采样", "电压", "通道"],
    "i2c": ["i2c"],
    "spi": ["spi"],
    "uart": ["uart", "串口", "波特率", "baud"],
    "exti": ["exti", "外部中断"],
}


@dataclass
class ExtractedParameters:
    frequency_hz: int | None = None
    duty_percent: int | None = None
    period_ms: int | None = None
    pin: str | None = None
    timer: str | None = None
    gpio_port: str | None = None
    cli_command_name: str | None = None
    baud_rate: int | None = None
    voltage: float | None = None
    raw_keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _extract_cli_command_name(user_request: str) -> str | None:
    for pattern in _CLI_COMMAND_RES:
        match = pattern.search(user_request)
        if match:
            return str(match.group("name")).strip().lower()

    if any(token in user_request.lower() for token in ("命令", "command", "cli")):
        quoted = re.search(r"[\"'`“”‘’](?P<name>[a-z_][a-z0-9_]*)[\"'`“”‘’]", user_request, re.IGNORECASE)
        if quoted:
            return str(quoted.group("name")).strip().lower()
    return None


def _extract_keywords(user_request: str) -> list[str]:
    lower = user_request.lower()
    found: list[str] = []
    for name, candidates in _KEYWORD_GROUPS.items():
        if any(candidate.lower() in lower for candidate in candidates):
            found.append(name)
    return found


def extract_parameters(user_request: str) -> ExtractedParameters:
    params = ExtractedParameters()

    frequency_match = _FREQUENCY_RE.search(user_request)
    if frequency_match:
        value = float(frequency_match.group("value"))
        unit = frequency_match.group("unit").lower()
        params.frequency_hz = int(round(value * FREQUENCY_UNITS[unit]))

    duty_match = _DUTY_RE.search(user_request)
    if duty_match:
        params.duty_percent = max(0, min(100, int(duty_match.group("value"))))

    period_match = _PERIOD_RE.search(user_request)
    if period_match:
        value = float(period_match.group("value"))
        unit = period_match.group("unit").lower()
        params.period_ms = int(round(value * TIME_UNITS_TO_MS[unit]))

    pin_match = _PIN_RE.search(user_request)
    if pin_match:
        port = pin_match.group("port").upper()
        index = pin_match.group("index")
        params.pin = f"P{port}{index}"
        params.gpio_port = f"GPIO{port}"

    timer_match = _TIMER_RE.search(user_request)
    if timer_match:
        params.timer = f"TIM{timer_match.group('index')}"

    baud_match = _BAUD_RE.search(user_request)
    if baud_match:
        params.baud_rate = int(baud_match.group("value"))

    voltage_match = _VOLTAGE_RE.search(user_request)
    if voltage_match:
        params.voltage = float(voltage_match.group("value"))

    params.cli_command_name = _extract_cli_command_name(user_request)
    params.raw_keywords = _extract_keywords(user_request)
    return params
