from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - env specific
    raise RuntimeError(
        "PyYAML is required. Run agent_workbench\\bin\\setup.bat first."
    ) from exc


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload or {}


class HardwareKnowledge:
    def __init__(self, root: Path):
        self.root = root
        self.clock = _load_yaml(root / "stm32f1_clock.yaml")
        self.timer_pin_map = _load_yaml(root / "stm32f1_timer_pin_map.yaml")
        self.user_code_regions = _load_yaml(root / "stm32f1_user_code_regions.yaml")

    def default_clock_context(self) -> dict[str, Any]:
        return {
            "mcu_family": self.clock.get("mcu_family", "stm32f1"),
            "system_clock_hz": int(self.clock.get("system_clock_hz", 72_000_000)),
            "timer_clocks": self.clock.get("timer_clocks", {}),
            "frequency_formula": self.clock.get(
                "frequency_formula",
                "f = system_clock / ((Prescaler + 1) * (Period + 1))",
            ),
        }

    def default_user_code_regions(self) -> list[dict[str, Any]]:
        return list(self.user_code_regions.get("user_code_regions", []))

    def timer_channels_for_pin(self, pin: str | None) -> list[str]:
        if not pin:
            return []
        channels = self.timer_pin_map.get("pin_to_timer_channels", {}).get(pin.upper(), [])
        return [str(item).strip() for item in channels if str(item).strip()]

    def pin_details_for_channel(self, channel: str | None) -> dict[str, Any]:
        if not channel:
            return {}
        details = self.timer_pin_map.get("timer_channel_to_pin", {}).get(channel, {})
        return dict(details or {})

    def _preset_for_frequency(self, frequency_hz: int | None) -> dict[str, Any] | None:
        if not frequency_hz:
            return None
        for item in self.timer_pin_map.get("preset_frequencies", []):
            if int(item.get("frequency_hz", 0)) == int(frequency_hz):
                return dict(item)
        return None

    def _derive_timer_dividers(self, timer_clock_hz: int, frequency_hz: int) -> tuple[int, int]:
        target_divisor = max(1, int(round(timer_clock_hz / max(frequency_hz, 1))))
        prescaler = max(0, min(65_535, (target_divisor - 1) // 65_536))
        period = max(0, min(65_535, int(round(timer_clock_hz / ((prescaler + 1) * frequency_hz))) - 1))
        if period <= 0:
            period = max(0, min(65_535, target_divisor - 1))
        return prescaler, period

    def build_pwm_context(
        self,
        *,
        frequency_hz: int | None,
        duty_percent: int | None,
        pin: str | None,
        requested_timer: str | None = None,
    ) -> dict[str, Any]:
        clock_ctx = self.default_clock_context()
        normalized_pin = (pin or "").upper()
        requested_timer = (requested_timer or "").upper()
        candidates = self.timer_channels_for_pin(normalized_pin)
        if requested_timer:
            filtered = [channel for channel in candidates if channel.startswith(requested_timer)]
            if filtered:
                candidates = filtered

        recommended = candidates[0] if candidates else None
        pin_details = self.pin_details_for_channel(recommended)
        timer_name = recommended.split("_CH", 1)[0] if recommended else requested_timer or None
        channel_suffix = recommended.split("_CH", 1)[1] if recommended and "_CH" in recommended else None
        timer_clock_hz = int(clock_ctx.get("timer_clocks", {}).get(timer_name or "", clock_ctx["system_clock_hz"]))

        target_frequency = int(frequency_hz or 1_000)
        target_duty = int(duty_percent if duty_percent is not None else 50)
        preset = self._preset_for_frequency(target_frequency)
        if preset:
            prescaler = int(preset["prescaler"])
            period = int(preset["period"])
            rationale = str(preset.get("description", "preset frequency match"))
        else:
            prescaler, period = self._derive_timer_dividers(timer_clock_hz, target_frequency)
            rationale = "derived from timer clock and requested frequency"

        ccr = max(0, min(period + 1, int(round((period + 1) * (target_duty / 100.0)))))
        estimated_frequency = timer_clock_hz / ((prescaler + 1) * (period + 1))
        handle_name = ""
        if timer_name and timer_name.upper().startswith("TIM"):
            handle_name = f"htim{timer_name[3:]}"

        return {
            "clock": clock_ctx,
            "pin_mapping": {
                "requested_pin": normalized_pin or None,
                "candidates": candidates,
                "recommended": recommended,
                "alternate_function_mode": pin_details.get("af"),
                "gpio_port": f"GPIO{normalized_pin[1]}" if len(normalized_pin) >= 2 else None,
                "gpio_pin_define": f"GPIO_PIN_{normalized_pin[2:]}" if len(normalized_pin) >= 3 else None,
                "details": pin_details,
            },
            "timer_config": {
                "timer": timer_name,
                "channel": f"TIM_CHANNEL_{channel_suffix}" if channel_suffix else None,
                "handle_name": handle_name or None,
                "target_frequency_hz": target_frequency,
                "estimated_frequency_hz": int(round(estimated_frequency)),
                "duty_percent": target_duty,
                "prescaler": prescaler,
                "period": period,
                "ccr": ccr,
                "frequency_formula": clock_ctx.get("frequency_formula"),
                "rationale": rationale,
            },
        }
