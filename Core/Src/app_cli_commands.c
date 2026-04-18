#include "app_cli_commands.h"
#include "app_diag_modbus.h"
#include "app_runtime.h"
#include "app_serial_config.h"

#include <string.h>

#define APP_LED_ON GPIO_PIN_SET
#define APP_LED_OFF GPIO_PIN_RESET

typedef enum
{
  APP_LED_TARGET_INVALID = 0,
  APP_LED_TARGET_RED,
  APP_LED_TARGET_GREEN,
  APP_LED_TARGET_BLUE,
  APP_LED_TARGET_ALL
} AppLedTarget;

typedef enum
{
  APP_LED_ACTION_INVALID = 0,
  APP_LED_ACTION_ON,
  APP_LED_ACTION_OFF,
  APP_LED_ACTION_TOGGLE
} AppLedAction;

static void AppCli_Help(CliContext *cli, int argc, char **argv);
static void AppCli_Status(CliContext *cli, int argc, char **argv);
static void AppCli_Led(CliContext *cli, int argc, char **argv);
static void AppCli_Red(CliContext *cli, int argc, char **argv);
static void AppCli_Green(CliContext *cli, int argc, char **argv);
static void AppCli_Blue(CliContext *cli, int argc, char **argv);
static void AppCli_All(CliContext *cli, int argc, char **argv);
static void AppCli_LedStatus(CliContext *cli, int argc, char **argv);
static void AppCli_DiagStatus(CliContext *cli, int argc, char **argv);

static void AppCli_PrintCommandHelp(CliContext *cli, const CliCommand *command);
static void AppCli_PrintLedStatus(CliContext *cli, const char *name, GPIO_TypeDef *port, uint16_t pin);
static void AppCli_PrintDiagStatus(CliContext *cli);
static AppLedTarget AppCli_ParseTarget(const char *text);
static AppLedAction AppCli_ParseAction(const char *text);
static void AppCli_HandleLedCommand(CliContext *cli, const char *target_text, const char *action_text);
static void AppCli_WriteTargetState(AppLedTarget target, AppLedAction action);
static void AppCli_WriteOneLed(GPIO_TypeDef *port, uint16_t pin, AppLedAction action);
static const char *AppCli_GetLedStateText(GPIO_TypeDef *port, uint16_t pin);

static const CliCommand app_cli_commands[] =
{
  { "help", "List commands or show help for one command.", "help [command]", AppCli_Help },
  { "status", "Show UART and LED status.", "status", AppCli_Status },
  { "led", "Control one LED or all LEDs.", "led <red|green|blue|all> <on|off|toggle>", AppCli_Led },
  { "red", "Shortcut for 'led red ...'.", "red <on|off|toggle>", AppCli_Red },
  { "green", "Shortcut for 'led green ...'.", "green <on|off|toggle>", AppCli_Green },
  { "blue", "Shortcut for 'led blue ...'.", "blue <on|off|toggle>", AppCli_Blue },
  { "all", "Shortcut for 'led all ...'.", "all <on|off|toggle>", AppCli_All },
  { "led_status", "Print the on/off state of all LEDs.", "led_status", AppCli_LedStatus },
  { "diag_status", "Show diagnostic UART and Modbus state.", "diag_status", AppCli_DiagStatus }
};

const CliCommand *AppCli_GetCommands(size_t *count)
{
  if (count != NULL)
  {
    *count = sizeof(app_cli_commands) / sizeof(app_cli_commands[0]);
  }

  return app_cli_commands;
}

static void AppCli_Help(CliContext *cli, int argc, char **argv)
{
  size_t index = 0U;
  const CliCommand *command = NULL;

  if (argc > 2)
  {
    Cli_RecordCommandError(NULL);
    Cli_WriteString(cli, "Usage: help [command]\r\n");
    return;
  }

  if (argc == 1)
  {
    Cli_WriteString(cli, "Available commands:\r\n");
    for (index = 0U; index < Cli_GetCommandCount(cli); ++index)
    {
      command = Cli_GetCommandAt(cli, index);
      Cli_Printf(cli, "  %-8s %s\r\n", command->name, command->summary);
    }
    Cli_WriteString(cli, "Use 'help <command>' for details.\r\n");
    return;
  }

  command = Cli_FindCommand(cli, argv[1]);
  if (command == NULL)
  {
    Cli_RecordCommandError(NULL);
    Cli_Printf(cli, "[error] no such command: %s\r\n", argv[1]);
    return;
  }

  AppCli_PrintCommandHelp(cli, command);
}

static void AppCli_Status(CliContext *cli, int argc, char **argv)
{
  (void)argc;
  (void)argv;

  Cli_WriteString(cli, "System status:\r\n");
  Cli_Printf(cli, "  Debug UART: %s @ %lu 8N1\r\n", APP_DEBUG_UART_LABEL, (unsigned long)APP_DEBUG_UART_BAUDRATE);
  Cli_Printf(cli, "  Debug Pins: %s\r\n", APP_DEBUG_UART_PINS_LABEL);
  AppCli_PrintLedStatus(cli, "RED", LED_RED_GPIO_Port, LED_RED_Pin);
  AppCli_PrintLedStatus(cli, "GREEN", LED_GREEN_GPIO_Port, LED_GREEN_Pin);
  AppCli_PrintLedStatus(cli, "BLUE", LED_BLUE_GPIO_Port, LED_BLUE_Pin);
  Cli_Printf(
    cli,
    "  Diag UART: %s @ %lu 8N1, addr=0x%02X\r\n",
    APP_DIAG_UART_LABEL,
    (unsigned long)APP_DIAG_UART_BAUDRATE,
    APP_DIAG_MODBUS_SLAVE_ADDRESS);
  Cli_Printf(cli, "  Diag Pins: %s\r\n", APP_DIAG_UART_PINS_LABEL);
}

static void AppCli_Led(CliContext *cli, int argc, char **argv)
{
  if (argc != 3)
  {
    Cli_RecordCommandError(NULL);
    Cli_WriteString(cli, "Usage: led <red|green|blue|all> <on|off|toggle>\r\n");
    return;
  }

  AppCli_HandleLedCommand(cli, argv[1], argv[2]);
}

static void AppCli_Red(CliContext *cli, int argc, char **argv)
{
  if (argc != 2)
  {
    Cli_RecordCommandError(NULL);
    Cli_WriteString(cli, "Usage: red <on|off|toggle>\r\n");
    return;
  }

  AppCli_HandleLedCommand(cli, "red", argv[1]);
}

static void AppCli_Green(CliContext *cli, int argc, char **argv)
{
  if (argc != 2)
  {
    Cli_RecordCommandError(NULL);
    Cli_WriteString(cli, "Usage: green <on|off|toggle>\r\n");
    return;
  }

  AppCli_HandleLedCommand(cli, "green", argv[1]);
}

static void AppCli_Blue(CliContext *cli, int argc, char **argv)
{
  if (argc != 2)
  {
    Cli_RecordCommandError(NULL);
    Cli_WriteString(cli, "Usage: blue <on|off|toggle>\r\n");
    return;
  }

  AppCli_HandleLedCommand(cli, "blue", argv[1]);
}

static void AppCli_All(CliContext *cli, int argc, char **argv)
{
  if (argc != 2)
  {
    Cli_RecordCommandError(NULL);
    Cli_WriteString(cli, "Usage: all <on|off|toggle>\r\n");
    return;
  }

  AppCli_HandleLedCommand(cli, "all", argv[1]);
}

static void AppCli_LedStatus(CliContext *cli, int argc, char **argv)
{
  (void)argc;
  (void)argv;

  Cli_WriteString(cli, "LED status:\r\n");
  AppCli_PrintLedStatus(cli, "RED", LED_RED_GPIO_Port, LED_RED_Pin);
  AppCli_PrintLedStatus(cli, "GREEN", LED_GREEN_GPIO_Port, LED_GREEN_Pin);
  AppCli_PrintLedStatus(cli, "BLUE", LED_BLUE_GPIO_Port, LED_BLUE_Pin);
}

static void AppCli_DiagStatus(CliContext *cli, int argc, char **argv)
{
  (void)argc;
  (void)argv;

  AppCli_PrintDiagStatus(cli);
}

static void AppCli_PrintCommandHelp(CliContext *cli, const CliCommand *command)
{
  Cli_Printf(cli, "%s\r\n", command->name);
  Cli_Printf(cli, "  %s\r\n", command->summary);
  Cli_Printf(cli, "  Usage: %s\r\n", command->usage);
}

static void AppCli_PrintLedStatus(CliContext *cli, const char *name, GPIO_TypeDef *port, uint16_t pin)
{
  Cli_Printf(cli, "  LED %-5s: %s\r\n", name, AppCli_GetLedStateText(port, pin));
}

static void AppCli_PrintDiagStatus(CliContext *cli)
{
  DiagLinkStats link_stats;
  AppDiagModbusState modbus_state;

  DiagLink_GetStats(&g_diag_link, &link_stats);
  AppDiagModbus_GetState(&g_diag_modbus, &modbus_state);

  Cli_WriteString(cli, "Diagnostic port status:\r\n");
  Cli_Printf(cli, "  UART: %s @ %lu 8N1\r\n", APP_DIAG_UART_LABEL, (unsigned long)APP_DIAG_UART_BAUDRATE);
  Cli_Printf(cli, "  Pins: %s\r\n", APP_DIAG_UART_PINS_LABEL);
  Cli_Printf(cli, "  Frame gap: %lu ms\r\n", (unsigned long)APP_DIAG_FRAME_GAP_MS);
  Cli_Printf(cli, "  Modbus slave: 0x%02X\r\n", modbus_state.slave_address);
  Cli_Printf(
    cli,
    "  Link stats: rx_bytes=%lu rx_frames=%lu tx_frames=%lu dropped=%lu uart_err=%lu\r\n",
    (unsigned long)link_stats.rx_bytes,
    (unsigned long)link_stats.rx_frames,
    (unsigned long)link_stats.tx_frames,
    (unsigned long)link_stats.dropped_frames,
    (unsigned long)link_stats.uart_errors);
  Cli_Printf(
    cli,
    "  Modbus stats: handled=%lu ignored=%lu crc_err=%lu exceptions=%lu\r\n",
    (unsigned long)modbus_state.handled_requests,
    (unsigned long)modbus_state.ignored_frames,
    (unsigned long)modbus_state.crc_errors,
    (unsigned long)modbus_state.exception_responses);
  Cli_Printf(
    cli,
    "  Last frame: func=0x%02X reg=0x%04X arg=0x%04X exc=0x%02X\r\n",
    modbus_state.last_function,
    modbus_state.last_register,
    modbus_state.last_argument,
    modbus_state.last_exception);
}

static AppLedTarget AppCli_ParseTarget(const char *text)
{
  if (strcmp(text, "red") == 0)
  {
    return APP_LED_TARGET_RED;
  }

  if (strcmp(text, "green") == 0)
  {
    return APP_LED_TARGET_GREEN;
  }

  if (strcmp(text, "blue") == 0)
  {
    return APP_LED_TARGET_BLUE;
  }

  if (strcmp(text, "all") == 0)
  {
    return APP_LED_TARGET_ALL;
  }

  return APP_LED_TARGET_INVALID;
}

static AppLedAction AppCli_ParseAction(const char *text)
{
  if (strcmp(text, "on") == 0)
  {
    return APP_LED_ACTION_ON;
  }

  if (strcmp(text, "off") == 0)
  {
    return APP_LED_ACTION_OFF;
  }

  if (strcmp(text, "toggle") == 0)
  {
    return APP_LED_ACTION_TOGGLE;
  }

  return APP_LED_ACTION_INVALID;
}

static void AppCli_HandleLedCommand(CliContext *cli, const char *target_text, const char *action_text)
{
  AppLedTarget target = AppCli_ParseTarget(target_text);
  AppLedAction action = AppCli_ParseAction(action_text);

  if (target == APP_LED_TARGET_INVALID)
  {
    Cli_RecordCommandError(NULL);
    Cli_Printf(cli, "[error] invalid LED target: %s\r\n", target_text);
    return;
  }

  if (action == APP_LED_ACTION_INVALID)
  {
    Cli_RecordCommandError(NULL);
    Cli_Printf(cli, "[error] invalid LED action: %s\r\n", action_text);
    return;
  }

  AppCli_WriteTargetState(target, action);
  Cli_Printf(cli, "[ok] %s -> %s\r\n", target_text, action_text);
  AppCli_Status(cli, 0, NULL);
}

static void AppCli_WriteTargetState(AppLedTarget target, AppLedAction action)
{
  switch (target)
  {
    case APP_LED_TARGET_RED:
      AppCli_WriteOneLed(LED_RED_GPIO_Port, LED_RED_Pin, action);
      break;

    case APP_LED_TARGET_GREEN:
      AppCli_WriteOneLed(LED_GREEN_GPIO_Port, LED_GREEN_Pin, action);
      break;

    case APP_LED_TARGET_BLUE:
      AppCli_WriteOneLed(LED_BLUE_GPIO_Port, LED_BLUE_Pin, action);
      break;

    case APP_LED_TARGET_ALL:
      AppCli_WriteOneLed(LED_RED_GPIO_Port, LED_RED_Pin, action);
      AppCli_WriteOneLed(LED_GREEN_GPIO_Port, LED_GREEN_Pin, action);
      AppCli_WriteOneLed(LED_BLUE_GPIO_Port, LED_BLUE_Pin, action);
      break;

    default:
      break;
  }
}

static void AppCli_WriteOneLed(GPIO_TypeDef *port, uint16_t pin, AppLedAction action)
{
  GPIO_PinState next_state = APP_LED_OFF;

  if (action == APP_LED_ACTION_TOGGLE)
  {
    HAL_GPIO_TogglePin(port, pin);
    return;
  }

  next_state = (action == APP_LED_ACTION_ON) ? APP_LED_ON : APP_LED_OFF;
  HAL_GPIO_WritePin(port, pin, next_state);
}

static const char *AppCli_GetLedStateText(GPIO_TypeDef *port, uint16_t pin)
{
  return (HAL_GPIO_ReadPin(port, pin) == APP_LED_ON) ? "on" : "off";
}
