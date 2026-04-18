#ifndef __DIAG_LINK_H
#define __DIAG_LINK_H

#include "main.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define DIAG_LINK_RX_BUFFER_SIZE 128U
#define DIAG_LINK_TX_BUFFER_SIZE 128U

typedef uint16_t (*DiagLinkRequestHandler)(
  const uint8_t *request,
  uint16_t request_length,
  uint8_t *response,
  uint16_t response_capacity,
  void *user_context);

typedef struct
{
  uint32_t rx_bytes;
  uint32_t rx_frames;
  uint32_t tx_bytes;
  uint32_t tx_frames;
  uint32_t dropped_frames;
  uint32_t uart_errors;
  uint16_t last_request_length;
  uint16_t last_response_length;
} DiagLinkStats;

typedef struct
{
  UART_HandleTypeDef *uart;
  DiagLinkRequestHandler handler;
  void *handler_user_context;
  uint8_t rx_byte;
  uint8_t rx_buffer[DIAG_LINK_RX_BUFFER_SIZE];
  uint8_t tx_buffer[DIAG_LINK_TX_BUFFER_SIZE];
  uint16_t rx_length;
  uint16_t frame_gap_ms;
  uint32_t last_rx_tick;
  volatile uint8_t frame_overflow;
  volatile uint8_t uart_error_pending;
  DiagLinkStats stats;
} DiagLinkContext;

void DiagLink_Init(
  DiagLinkContext *context,
  UART_HandleTypeDef *uart,
  uint16_t frame_gap_ms,
  DiagLinkRequestHandler handler,
  void *handler_user_context);
HAL_StatusTypeDef DiagLink_Start(DiagLinkContext *context);
void DiagLink_Process(DiagLinkContext *context);
void DiagLink_HandleRxComplete(DiagLinkContext *context, UART_HandleTypeDef *huart);
void DiagLink_HandleError(DiagLinkContext *context, UART_HandleTypeDef *huart);
void DiagLink_GetStats(const DiagLinkContext *context, DiagLinkStats *stats);

#ifdef __cplusplus
}
#endif

#endif /* __DIAG_LINK_H */
