#include "cli.h"

#include <ctype.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#define CLI_PROMPT "cli> "

static HAL_StatusTypeDef Cli_ArmReceive(CliContext *cli);
static void Cli_ResetInputState(CliContext *cli);
static void CliStats_CopyLastCommand(const char *line);
static void Cli_EnqueueByte(CliContext *cli, uint8_t byte);
static uint8_t Cli_DequeueByte(CliContext *cli, uint8_t *byte);
static void Cli_ProcessByte(CliContext *cli, uint8_t byte);
static void Cli_ExecuteLine(CliContext *cli);
static int Cli_Tokenize(char *line, char **argv, size_t max_args);
static void Cli_WriteByteIsr(UART_HandleTypeDef *huart, uint8_t byte);
static void Cli_WriteStringIsr(UART_HandleTypeDef *huart, const char *text);

volatile DebugCliStatsData DebugCliStats;

void Cli_Init(CliContext *cli, UART_HandleTypeDef *uart, const CliCommand *commands, size_t command_count)
{
  memset(cli, 0, sizeof(*cli));
  cli->uart = uart;
  cli->commands = commands;
  cli->command_count = command_count;
  memset((void *)&DebugCliStats, 0, sizeof(DebugCliStats));
}

HAL_StatusTypeDef Cli_Start(CliContext *cli)
{
  Cli_WriteString(cli, "\r\nSTM32 UART CLI ready.\r\n");
  Cli_WriteString(cli, "Console: USART2 @ 115200 8N1, TX=PA2, RX=PA3\r\n");
  Cli_WriteString(cli, "Type 'help' to list commands.\r\n\r\n");
  Cli_ShowPrompt(cli);

  return Cli_ArmReceive(cli);
}

void Cli_Process(CliContext *cli)
{
  uint8_t byte = 0U;

  if (cli->uart_error != 0U)
  {
    cli->uart_error = 0U;
    Cli_ResetInputState(cli);
    Cli_WriteString(cli, "\r\n[warn] UART receive error, input state reset.\r\n");
    Cli_ShowPrompt(cli);
  }

  if (cli->rx_overflow != 0U)
  {
    cli->rx_overflow = 0U;
    Cli_ResetInputState(cli);
    Cli_WriteString(cli, "\r\n[error] RX queue overflow, current input discarded.\r\n");
    Cli_ShowPrompt(cli);
  }

  while (Cli_DequeueByte(cli, &byte) != 0U)
  {
    Cli_ProcessByte(cli, byte);
  }
}

void Cli_HandleRxComplete(CliContext *cli, UART_HandleTypeDef *huart)
{
  if (huart != cli->uart)
  {
    return;
  }

  DebugCliStats.rx_bytes++;

  if ((cli->rx_byte == '\r') || (cli->rx_byte == '\n'))
  {
    if ((cli->rx_byte == '\n') && (cli->rx_cr_seen != 0U))
    {
      cli->rx_cr_seen = 0U;
    }
    else
    {
      Cli_WriteStringIsr(huart, "\r\n");
      cli->rx_cr_seen = (cli->rx_byte == '\r') ? 1U : 0U;
    }
  }
  else if ((cli->rx_byte == '\b') || (cli->rx_byte == 0x7FU))
  {
    cli->rx_cr_seen = 0U;
    Cli_WriteStringIsr(huart, "\b \b");
  }
  else if (isprint(cli->rx_byte) != 0)
  {
    cli->rx_cr_seen = 0U;
    Cli_WriteByteIsr(huart, cli->rx_byte);
  }
  else
  {
    cli->rx_cr_seen = 0U;
  }

  Cli_EnqueueByte(cli, cli->rx_byte);
  (void)Cli_ArmReceive(cli);
}

void Cli_HandleError(CliContext *cli, UART_HandleTypeDef *huart)
{
  if (huart != cli->uart)
  {
    return;
  }

  DebugCliStats.uart_error++;
  cli->uart_error = 1U;
  __HAL_UART_CLEAR_OREFLAG(huart);
  __HAL_UART_CLEAR_NEFLAG(huart);
  __HAL_UART_CLEAR_FEFLAG(huart);
  __HAL_UART_CLEAR_PEFLAG(huart);
  (void)Cli_ArmReceive(cli);
}

void Cli_Write(CliContext *cli, const uint8_t *data, uint16_t length)
{
  if ((cli == NULL) || (cli->uart == NULL) || (data == NULL) || (length == 0U))
  {
    return;
  }

  (void)HAL_UART_Transmit(cli->uart, (uint8_t *)data, length, HAL_MAX_DELAY);
}

void Cli_WriteString(CliContext *cli, const char *text)
{
  if (text == NULL)
  {
    return;
  }

  Cli_Write(cli, (const uint8_t *)text, (uint16_t)strlen(text));
}

void Cli_Printf(CliContext *cli, const char *format, ...)
{
  char buffer[160];
  va_list args;
  int length = 0;

  va_start(args, format);
  length = vsnprintf(buffer, sizeof(buffer), format, args);
  va_end(args);

  if (length <= 0)
  {
    return;
  }

  if ((size_t)length >= sizeof(buffer))
  {
    length = (int)(sizeof(buffer) - 1U);
  }

  Cli_Write(cli, (const uint8_t *)buffer, (uint16_t)length);
}

void Cli_ShowPrompt(CliContext *cli)
{
  Cli_WriteString(cli, CLI_PROMPT);
}

void Cli_RecordCommandError(const char *command_text)
{
  DebugCliStats.cmd_err++;
  if ((command_text != NULL) && (command_text[0] != '\0'))
  {
    CliStats_CopyLastCommand(command_text);
  }
}

const CliCommand *Cli_FindCommand(const CliContext *cli, const char *name)
{
  size_t index = 0U;

  if ((cli == NULL) || (name == NULL))
  {
    return NULL;
  }

  for (index = 0U; index < cli->command_count; ++index)
  {
    if (strcmp(cli->commands[index].name, name) == 0)
    {
      return &cli->commands[index];
    }
  }

  return NULL;
}

size_t Cli_GetCommandCount(const CliContext *cli)
{
  return (cli == NULL) ? 0U : cli->command_count;
}

const CliCommand *Cli_GetCommandAt(const CliContext *cli, size_t index)
{
  if ((cli == NULL) || (index >= cli->command_count))
  {
    return NULL;
  }

  return &cli->commands[index];
}

static HAL_StatusTypeDef Cli_ArmReceive(CliContext *cli)
{
  return HAL_UART_Receive_IT(cli->uart, &cli->rx_byte, 1U);
}

static void Cli_ResetInputState(CliContext *cli)
{
  cli->rx_head = 0U;
  cli->rx_tail = 0U;
  cli->line_length = 0U;
  cli->last_eol_was_cr = 0U;
  cli->rx_cr_seen = 0U;
  cli->line_overflow = 0U;
}

static void CliStats_CopyLastCommand(const char *line)
{
  size_t index = 0U;

  if (line == NULL)
  {
    DebugCliStats.last_cmd[0] = '\0';
    return;
  }

  while ((line[index] != '\0') && (index < (sizeof(DebugCliStats.last_cmd) - 1U)))
  {
    DebugCliStats.last_cmd[index] = line[index];
    index++;
  }

  DebugCliStats.last_cmd[index] = '\0';
}

static void Cli_EnqueueByte(CliContext *cli, uint8_t byte)
{
  uint16_t next_head = (uint16_t)((cli->rx_head + 1U) % CLI_RX_QUEUE_SIZE);

  if (next_head == cli->rx_tail)
  {
    DebugCliStats.rx_overflow++;
    cli->rx_overflow = 1U;
    return;
  }

  cli->rx_queue[cli->rx_head] = byte;
  cli->rx_head = next_head;
}

static uint8_t Cli_DequeueByte(CliContext *cli, uint8_t *byte)
{
  if (cli->rx_tail == cli->rx_head)
  {
    return 0U;
  }

  *byte = cli->rx_queue[cli->rx_tail];
  cli->rx_tail = (uint16_t)((cli->rx_tail + 1U) % CLI_RX_QUEUE_SIZE);
  return 1U;
}

static void Cli_ProcessByte(CliContext *cli, uint8_t byte)
{
  if ((byte == '\r') || (byte == '\n'))
  {
    if ((byte == '\n') && (cli->last_eol_was_cr != 0U))
    {
      cli->last_eol_was_cr = 0U;
      return;
    }

    cli->last_eol_was_cr = (byte == '\r') ? 1U : 0U;
    DebugCliStats.rx_lines++;

    if (cli->line_overflow != 0U)
    {
      cli->line_buffer[CLI_LINE_BUFFER_SIZE - 1U] = '\0';
      DebugCliStats.cmd_err++;
      CliStats_CopyLastCommand(cli->line_buffer);
      Cli_WriteString(cli, "[error] command too long, max 63 chars.\r\n");
    }
    else
    {
      cli->line_buffer[cli->line_length] = '\0';
      Cli_ExecuteLine(cli);
    }

    cli->line_length = 0U;
    cli->line_overflow = 0U;
    Cli_ShowPrompt(cli);
    return;
  }

  cli->last_eol_was_cr = 0U;

  if ((byte == '\b') || (byte == 0x7FU))
  {
    if (cli->line_length > 0U)
    {
      cli->line_length--;
    }
    return;
  }

  if (isprint(byte) == 0)
  {
    return;
  }

  if (cli->line_length >= (CLI_LINE_BUFFER_SIZE - 1U))
  {
    cli->line_overflow = 1U;
    return;
  }

  cli->line_buffer[cli->line_length++] = (char)byte;
}

static void Cli_ExecuteLine(CliContext *cli)
{
  char *argv[CLI_MAX_ARGS];
  int argc = 0;
  const CliCommand *command = NULL;

  CliStats_CopyLastCommand(cli->line_buffer);
  argc = Cli_Tokenize(cli->line_buffer, argv, CLI_MAX_ARGS);
  if (argc == 0)
  {
    return;
  }

  if (argc < 0)
  {
    DebugCliStats.cmd_err++;
    Cli_WriteString(cli, "[error] too many arguments.\r\n");
    return;
  }

  command = Cli_FindCommand(cli, argv[0]);
  if (command == NULL)
  {
    DebugCliStats.cmd_err++;
    Cli_Printf(cli, "[error] unknown command: %s\r\n", argv[0]);
    Cli_WriteString(cli, "Type 'help' to list commands.\r\n");
    return;
  }

  DebugCliStats.cmd_ok++;
  command->handler(cli, argc, argv);
}

static int Cli_Tokenize(char *line, char **argv, size_t max_args)
{
  int argc = 0;
  char *cursor = line;

  while (*cursor != '\0')
  {
    while (isspace((unsigned char)*cursor) != 0)
    {
      cursor++;
    }

    if (*cursor == '\0')
    {
      break;
    }

    if ((size_t)argc >= max_args)
    {
      return -1;
    }

    argv[argc++] = cursor;

    while ((*cursor != '\0') && (isspace((unsigned char)*cursor) == 0))
    {
      cursor++;
    }

    if (*cursor == '\0')
    {
      break;
    }

    *cursor++ = '\0';
  }

  return argc;
}

static void Cli_WriteByteIsr(UART_HandleTypeDef *huart, uint8_t byte)
{
  uint32_t timeout = 0xFFFFU;

  while (((huart->Instance->SR & USART_SR_TXE) == 0U) && (timeout > 0U))
  {
    timeout--;
  }

  if (timeout == 0U)
  {
    return;
  }

  huart->Instance->DR = byte;
}

static void Cli_WriteStringIsr(UART_HandleTypeDef *huart, const char *text)
{
  while ((*text) != '\0')
  {
    Cli_WriteByteIsr(huart, (uint8_t)(*text));
    text++;
  }
}
