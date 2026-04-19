from __future__ import annotations

import unittest

from agent_workbench.core.param_extractor import extract_parameters


class ParamExtractorTests(unittest.TestCase):
    def test_extract_pwm_parameters(self) -> None:
        params = extract_parameters("给STM32添加PWM蜂鸣器控制，频率1kHz，PA8引脚，占空比50%")

        self.assertEqual(params.frequency_hz, 1000)
        self.assertEqual(params.pin, "PA8")
        self.assertEqual(params.gpio_port, "GPIOA")
        self.assertEqual(params.duty_percent, 50)

    def test_extract_cli_command_name(self) -> None:
        params = extract_parameters("添加一个CLI命令uptime显示系统运行了多少秒")

        self.assertEqual(params.cli_command_name, "uptime")

    def test_extract_period_and_baud_rate(self) -> None:
        params = extract_parameters("串口回显每500ms输出一次，波特率115200")

        self.assertEqual(params.period_ms, 500)
        self.assertEqual(params.baud_rate, 115200)
