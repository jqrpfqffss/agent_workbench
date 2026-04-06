#ifndef __CLI_H
#define __CLI_H

#include "main.h"

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define CLI_RX_QUEUE_SIZE 128U
#define CLI_LINE_BUFFER_SIZE 64U
#define CLI_MAX_ARGS 8U

typedef struct CliContext CliContext;

typedef void (*CliCommandHandler)(CliContext *cli, int argc, char **argv);

typedef struct
{
  uint32_t rx_bytes;
  uint32_t rx_lines;
  uint32_t cmd_ok;
  uint32_t cmd_err;
  uint32_t rx_overflow;
  uint32_t uart_error;
  char last_cmd[32];
} DebugCliStatsData;

typedef struct
{
  const char *name;
  const char *summary;
  const char *usage;
  CliCommandHandler handler;
} CliCommand;

struct CliContext
{
  UART_HandleTypeDef *uart;
  uint8_t rx_byte;
  volatile uint16_t rx_head;
  volatile uint16_t rx_tail;
  uint8_t rx_queue[CLI_RX_QUEUE_SIZE];
  char line_buffer[CLI_LINE_BUFFER_SIZE];
  uint16_t line_length;
  uint8_t last_eol_was_cr;
  uint8_t rx_cr_seen;
  uint8_t line_overflow;
  volatile uint8_t rx_overflow;
  volatile uint8_t uart_error;
  const CliCommand *commands;
  size_t command_count;
};

extern volatile DebugCliStatsData DebugCliStats;

void Cli_Init(CliContext *cli, UART_HandleTypeDef *uart, const CliCommand *commands, size_t command_count);
HAL_StatusTypeDef Cli_Start(CliContext *cli);
void Cli_Process(CliContext *cli);
void Cli_HandleRxComplete(CliContext *cli, UART_HandleTypeDef *huart);
void Cli_HandleError(CliContext *cli, UART_HandleTypeDef *huart);

void Cli_Write(CliContext *cli, const uint8_t *data, uint16_t length);
void Cli_WriteString(CliContext *cli, const char *text);
void Cli_Printf(CliContext *cli, const char *format, ...);
void Cli_ShowPrompt(CliContext *cli);
void Cli_RecordCommandError(const char *command_text);

const CliCommand *Cli_FindCommand(const CliContext *cli, const char *name);
size_t Cli_GetCommandCount(const CliContext *cli);
const CliCommand *Cli_GetCommandAt(const CliContext *cli, size_t index);

#ifdef __cplusplus
}
#endif

#endif /* __CLI_H */
