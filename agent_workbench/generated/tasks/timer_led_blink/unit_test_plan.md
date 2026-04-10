# Unit Test Plan

- task_id: `timer_led_blink`
- goal: Add a hardware timer (TIM3) that blinks the RED LED (PB0) at approximately 1 Hz using interrupt-driven toggling.

## Unit Acceptance
- TIM3 is initialized with proper prescaler and auto-reload values for ~500ms period
- TIM3 interrupt handler toggles LED_RED_Pin
- Timer is started in main() after peripheral initialization
- Existing CLI and UART functionality remain unaffected