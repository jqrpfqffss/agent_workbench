# Unit Test Plan

- task_id: `autoflow_feature_tim3_red_led_pb0_1_hz`
- goal: 使用 TIM3 定时器让 RED LED(PB0) 以约 1 Hz 闪烁

## Unit Acceptance
- TIM3 is initialized with the expected prescaler and auto-reload values.
- TIM3 interrupt toggles LED_RED_Pin.
- Timer start is triggered after the existing peripheral initialization path.
- Existing UART CLI behavior remains available.