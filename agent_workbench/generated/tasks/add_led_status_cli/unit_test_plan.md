# Unit Test Plan

- task_id: `add_led_status_cli`
- goal: Add a CLI command 'led_status' that prints the on/off state of all three LEDs (RED, GREEN, BLUE) on the board.

## Unit Acceptance
- led_status handler prints each LED name followed by its state (on or off)
- led_status appears in help command output
- existing commands (help, status, led, red, green, blue, all) continue to work