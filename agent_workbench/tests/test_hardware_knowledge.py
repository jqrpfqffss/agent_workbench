from __future__ import annotations

import unittest
from pathlib import Path

from agent_workbench.core.hardware_knowledge import HardwareKnowledge


class HardwareKnowledgeTests(unittest.TestCase):
    def test_pwm_context_for_pa8_1khz(self) -> None:
        knowledge_root = Path(__file__).resolve().parents[1] / "templates" / "hardware_knowledge"
        knowledge = HardwareKnowledge(knowledge_root)

        context = knowledge.build_pwm_context(frequency_hz=1000, duty_percent=50, pin="PA8")

        self.assertEqual(context["pin_mapping"]["recommended"], "TIM1_CH1")
        self.assertEqual(context["timer_config"]["timer"], "TIM1")
        self.assertEqual(context["timer_config"]["channel"], "TIM_CHANNEL_1")
        self.assertEqual(context["timer_config"]["prescaler"], 71)
        self.assertEqual(context["timer_config"]["period"], 999)
        self.assertEqual(context["timer_config"]["ccr"], 500)
