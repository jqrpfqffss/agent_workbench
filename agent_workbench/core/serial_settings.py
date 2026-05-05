from __future__ import annotations

from typing import Any

SERIAL_DATA_BITS_ALLOWED = {5, 6, 7, 8}
SERIAL_PARITY_ALIASES = {
    "n": "none",
    "none": "none",
    "no": "none",
    "e": "even",
    "even": "even",
    "o": "odd",
    "odd": "odd",
    "m": "mark",
    "mark": "mark",
    "s": "space",
    "space": "space",
}
SERIAL_PARITY_LETTERS = {
    "none": "N",
    "even": "E",
    "odd": "O",
    "mark": "M",
    "space": "S",
}
SERIAL_STOP_BITS_ALIASES = {
    1: 1.0,
    1.0: 1.0,
    "1": 1.0,
    "1.0": 1.0,
    "one": 1.0,
    1.5: 1.5,
    "1.5": 1.5,
    "1_5": 1.5,
    "onepointfive": 1.5,
    "one_point_five": 1.5,
    2: 2.0,
    2.0: 2.0,
    "2": 2.0,
    "2.0": 2.0,
    "two": 2.0,
}


def _coerce_int(value: Any, *, field_name: str, section_name: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{section_name}.{field_name} must be an integer") from exc


def _normalize_data_bits(value: Any, *, section_name: str) -> int:
    data_bits = _coerce_int(value, field_name="data_bits", section_name=section_name)
    if data_bits not in SERIAL_DATA_BITS_ALLOWED:
        allowed = ", ".join(str(item) for item in sorted(SERIAL_DATA_BITS_ALLOWED))
        raise ValueError(f"{section_name}.data_bits must be one of: {allowed}")
    return data_bits


def _normalize_parity(value: Any, *, section_name: str) -> str:
    normalized = SERIAL_PARITY_ALIASES.get(str(value).strip().lower())
    if normalized is None:
        allowed = ", ".join(sorted({"none", "even", "odd", "mark", "space"}))
        raise ValueError(f"{section_name}.parity must be one of: {allowed}")
    return normalized


def _normalize_stop_bits(value: Any, *, section_name: str) -> float:
    lookup_key: Any = value
    if isinstance(value, str):
        lookup_key = value.strip().lower()
    normalized = SERIAL_STOP_BITS_ALIASES.get(lookup_key)
    if normalized is None:
        raise ValueError(f"{section_name}.stop_bits must be one of: 1, 1.5, 2")
    return float(normalized)


def normalize_serial_section(section: dict[str, Any], *, section_name: str) -> dict[str, Any]:
    normalized = dict(section)
    normalized["baudrate"] = _coerce_int(normalized.get("baudrate", 9600), field_name="baudrate", section_name=section_name)
    normalized["data_bits"] = _normalize_data_bits(
        normalized.get("data_bits", normalized.get("bytesize", 8)),
        section_name=section_name,
    )
    normalized["stop_bits"] = _normalize_stop_bits(
        normalized.get("stop_bits", normalized.get("stopbits", 1)),
        section_name=section_name,
    )
    normalized["parity"] = _normalize_parity(normalized.get("parity", "none"), section_name=section_name)
    return normalized


def serial_format_code(section: dict[str, Any]) -> str:
    stop_bits = float(section.get("stop_bits", 1.0))
    stop_bits_text = str(int(stop_bits)) if stop_bits.is_integer() else str(stop_bits)
    parity = str(section.get("parity", "none")).strip().lower()
    return f"{int(section.get('data_bits', 8))}{SERIAL_PARITY_LETTERS.get(parity, 'N')}{stop_bits_text}"


def pyserial_open_kwargs(
    section: dict[str, Any],
    serial_module: Any,
    *,
    timeout: float,
    write_timeout: float | None = None,
) -> dict[str, Any]:
    kwargs = {
        "port": str(section["port"]),
        "baudrate": int(section["baudrate"]),
        "timeout": float(timeout),
        "bytesize": getattr(
            serial_module,
            {
                5: "FIVEBITS",
                6: "SIXBITS",
                7: "SEVENBITS",
                8: "EIGHTBITS",
            }[int(section["data_bits"])],
            int(section["data_bits"]),
        ),
        "parity": getattr(
            serial_module,
            {
                "none": "PARITY_NONE",
                "even": "PARITY_EVEN",
                "odd": "PARITY_ODD",
                "mark": "PARITY_MARK",
                "space": "PARITY_SPACE",
            }[str(section["parity"]).strip().lower()],
            SERIAL_PARITY_LETTERS[str(section["parity"]).strip().lower()],
        ),
        "stopbits": getattr(
            serial_module,
            {
                1.0: "STOPBITS_ONE",
                1.5: "STOPBITS_ONE_POINT_FIVE",
                2.0: "STOPBITS_TWO",
            }[float(section["stop_bits"])],
            float(section["stop_bits"]),
        ),
    }
    if write_timeout is not None:
        kwargs["write_timeout"] = float(write_timeout)
    return kwargs


def powershell_serial_params(section: dict[str, Any]) -> dict[str, Any]:
    return {
        "port": str(section["port"]),
        "baudrate": int(section["baudrate"]),
        "data_bits": int(section["data_bits"]),
        "parity_name": str(section["parity"]).strip().title(),
        "stop_bits_name": {
            1.0: "One",
            1.5: "OnePointFive",
            2.0: "Two",
        }[float(section["stop_bits"])],
        "format_code": serial_format_code(section),
    }
