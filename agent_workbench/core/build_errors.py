from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .utils import WORKBENCH_ROOT


_GCC_WITH_COLUMN = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<column>\d+): (?P<level>fatal error|error|warning|note): (?P<message>.+)$"
)
_GCC_NO_COLUMN = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+): (?P<level>fatal error|error|warning|note): (?P<message>.+)$"
)
_UNDECLARED_RE = re.compile(r"'(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)'\s+undeclared", re.IGNORECASE)
_UNKNOWN_TYPE_RE = re.compile(r"unknown type name '(?P<type_name>[A-Za-z_][A-Za-z0-9_]*)'", re.IGNORECASE)
_UNDEFINED_REFERENCE_RE = re.compile(r"undefined reference to [`'](?P<symbol>[^`']+)[`']", re.IGNORECASE)
_MISSING_INCLUDE_RE = re.compile(r"(?P<header>[^:\s]+):\s+No such file or directory", re.IGNORECASE)

_HANDLE_TYPE_MAP = {
    "htim": "TIM_HandleTypeDef",
    "huart": "UART_HandleTypeDef",
    "hadc": "ADC_HandleTypeDef",
    "hspi": "SPI_HandleTypeDef",
    "hi2c": "I2C_HandleTypeDef",
}


@dataclass
class BuildError:
    file: str
    line: int
    column: int
    level: str
    error_code: str
    message: str
    category: str
    context_lines: list[str]
    suggested_fix: dict[str, Any]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@lru_cache(maxsize=1)
def _rule_library() -> dict[str, Any]:
    path = WORKBENCH_ROOT / "templates" / "build_error_rules.json"
    if not path.exists():
        return {"rules": [], "default": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_level(level_text: str) -> str:
    text = str(level_text).strip().lower()
    if "warning" in text:
        return "warning"
    if "note" in text:
        return "note"
    return "error"


def _resolve_source_path(file_text: str, source_root: Path | None) -> Path | None:
    candidate = Path(file_text)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None
    roots = [root for root in (source_root, Path.cwd()) if root is not None]
    for root in roots:
        resolved = (root / candidate).resolve()
        if resolved.exists():
            return resolved
    return None


def _context_lines(path: Path | None, line_number: int) -> list[str]:
    if path is None or not path.exists() or line_number <= 0:
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    start = max(0, line_number - 2)
    end = min(len(lines), line_number + 1)
    return [f"{index + 1}: {lines[index]}" for index in range(start, end)]


def _library_rule(message: str, level: str) -> dict[str, Any]:
    text = message.strip()
    library = _rule_library()
    for rule in library.get("rules", []):
        pattern = str(rule.get("pattern", "")).strip()
        if pattern and re.search(pattern, text, re.IGNORECASE):
            return dict(rule)
    if level == "warning":
        return {
            "code": "compiler_warning",
            "category": "warning",
            "recommended_action": "review_warning",
        }
    default = dict(library.get("default", {}))
    default.setdefault("code", "compiler_error")
    default.setdefault("category", "build")
    default.setdefault("recommended_action", "inspect_first_error")
    return default


def _handle_fix(symbol: str) -> dict[str, Any] | None:
    lower = symbol.lower()
    for prefix, handle_type in _HANDLE_TYPE_MAP.items():
        if lower.startswith(prefix):
            return {
                "pattern_matched": "undeclared_handle",
                "recommended_action": "add_declaration",
                "action_type": "add_declaration",
                "target_files": ["Core/Inc/main.h"],
                "target_region": "/* USER CODE BEGIN EFP */",
                "code_template": f"extern {handle_type} {symbol};",
                "code": f"extern {handle_type} {symbol};",
                "parameter_hints": {"symbol": symbol, "handle_type": handle_type},
                "reasoning": f"{symbol} is used like an STM32 HAL handle but is not declared.",
            }
    return None


def _build_structured_fix(
    message: str,
    *,
    error_code: str,
    category: str,
    level: str,
    file_text: str,
) -> dict[str, Any]:
    undeclared = _UNDECLARED_RE.search(message)
    if undeclared:
        symbol = undeclared.group("symbol")
        specific = _handle_fix(symbol)
        if specific is not None:
            return specific
        return {
            "pattern_matched": error_code,
            "recommended_action": "add_or_include_declaration",
            "action_type": "review_and_declare",
            "target_files": [file_text] if file_text else [],
            "target_region": "",
            "code_template": f"/* declare {symbol} before use */",
            "code": f"/* declare {symbol} before use */",
            "parameter_hints": {"symbol": symbol},
            "reasoning": f"{symbol} is referenced before a visible declaration or definition.",
        }

    unknown_type = _UNKNOWN_TYPE_RE.search(message)
    if unknown_type:
        type_name = unknown_type.group("type_name")
        code = '#include "main.h"'
        if type_name.endswith("_HandleTypeDef"):
            code = '#include "stm32f1xx_hal.h"'
        return {
            "pattern_matched": error_code,
            "recommended_action": "add_include_or_typedef",
            "action_type": "add_include",
            "target_files": [file_text] if file_text else [],
            "target_region": "top_of_file",
            "code_template": code,
            "code": code,
            "parameter_hints": {"type_name": type_name},
            "reasoning": f"{type_name} is unknown in the current translation unit.",
        }

    undefined_reference = _UNDEFINED_REFERENCE_RE.search(message)
    if undefined_reference:
        symbol = undefined_reference.group("symbol")
        return {
            "pattern_matched": error_code,
            "recommended_action": "add_definition_or_link_source",
            "action_type": "add_definition",
            "target_files": [file_text] if file_text else [],
            "target_region": "",
            "code_template": f"/* add definition for {symbol} or include its source file in the build */",
            "code": f"/* add definition for {symbol} or include its source file in the build */",
            "parameter_hints": {"symbol": symbol},
            "reasoning": f"The linker cannot find a definition for {symbol}.",
        }

    missing_include = _MISSING_INCLUDE_RE.search(message)
    if missing_include:
        header = missing_include.group("header")
        return {
            "pattern_matched": error_code,
            "recommended_action": "fix_include_path",
            "action_type": "add_include",
            "target_files": [file_text] if file_text else [],
            "target_region": "top_of_file",
            "code_template": f'#include "{header}"',
            "code": f'#include "{header}"',
            "parameter_hints": {"header": header},
            "reasoning": f"The compiler cannot locate header {header}.",
        }

    if level == "warning":
        return {
            "pattern_matched": error_code,
            "recommended_action": "review_warning",
            "action_type": "review_warning",
            "target_files": [file_text] if file_text else [],
            "target_region": "",
            "code_template": "/* review warning context */",
            "code": "/* review warning context */",
            "parameter_hints": {},
            "reasoning": "Warnings should be handled after the first blocking error is fixed.",
        }

    return {
        "pattern_matched": error_code,
        "recommended_action": "inspect_first_error",
        "action_type": "inspect_context",
        "target_files": [file_text] if file_text else [],
        "target_region": "",
        "code_template": "/* inspect the first compiler error and apply the smallest safe fix */",
        "code": "/* inspect the first compiler error and apply the smallest safe fix */",
        "parameter_hints": {},
        "reasoning": f"Use the structured context to fix the first {category} problem before addressing follow-on errors.",
    }


def _categorize(message: str, level: str = "error") -> tuple[str, str]:
    rule = _library_rule(message, level)
    return str(rule.get("category", "build")), str(rule.get("code", "compiler_error"))


def _parse_gcc_line(line: str, source_root: Path | None) -> BuildError | None:
    stripped = line.strip()
    for pattern in (_GCC_WITH_COLUMN, _GCC_NO_COLUMN):
        match = pattern.match(stripped)
        if not match:
            continue
        file_text = match.group("file").strip()
        message = match.group("message").strip()
        level = _normalize_level(match.group("level"))
        category, error_code = _categorize(message, level=level)
        line_number = int(match.group("line"))
        column = int(match.groupdict().get("column") or 0)
        return BuildError(
            file=file_text,
            line=line_number,
            column=column,
            level=level,
            error_code=error_code,
            message=message,
            category=category,
            context_lines=_context_lines(_resolve_source_path(file_text, source_root), line_number),
            suggested_fix=_build_structured_fix(
                message,
                error_code=error_code,
                category=category,
                level=level,
                file_text=file_text,
            ),
        )
    return None


def _parse_linker_line(line: str) -> BuildError | None:
    stripped = line.strip()
    if "undefined reference to" not in stripped.lower():
        return None
    category, error_code = _categorize(stripped, level="error")
    return BuildError(
        file="",
        line=0,
        column=0,
        level="error",
        error_code=error_code,
        message=stripped,
        category=category,
        context_lines=[],
        suggested_fix=_build_structured_fix(
            stripped,
            error_code=error_code,
            category=category,
            level="error",
            file_text="",
        ),
    )


def parse_build_log(log_path: Path, source_root: Path | None = None) -> list[BuildError]:
    if not log_path.exists():
        return []
    errors: list[BuildError] = []
    seen: set[tuple[str, int, int, str, str]] = set()
    for raw_line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw_line = raw_line.lstrip("\ufeff")
        parsed = _parse_gcc_line(raw_line, source_root) or _parse_linker_line(raw_line)
        if parsed is None:
            continue
        key = (parsed.file, parsed.line, parsed.column, parsed.level, parsed.message)
        if key in seen:
            continue
        seen.add(key)
        errors.append(parsed)
    return errors
