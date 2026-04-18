#include "diag_link.h"

#include <string.h>

static HAL_StatusTypeDef DiagLink_ArmReceive(DiagLinkContext *context);
static void DiagLink_ResetFrame(DiagLinkContext *context);

void DiagLink_Init(
  DiagLinkContext *context,
  UART_HandleTypeDef *uart,
  uint16_t frame_gap_ms,
  DiagLinkRequestHandler handler,
  void *handler_user_context)
{
  memset(context, 0, sizeof(*context));
  context->uart = uart;
  context->frame_gap_ms = frame_gap_ms;
  context->handler = handler;
  context->handler_user_context = handler_user_context;
}

HAL_StatusTypeDef DiagLink_Start(DiagLinkContext *context)
{
  return DiagLink_ArmReceive(context);
}

void DiagLink_Process(DiagLinkContext *context)
{
  uint16_t response_length = 0U;

  if ((context == NULL) || (context->uart == NULL))
  {
    return;
  }

  if (context->uart_error_pending != 0U)
  {
    context->uart_error_pending = 0U;
    DiagLink_ResetFrame(context);
  }

  if (context->frame_overflow != 0U)
  {
    context->frame_overflow = 0U;
    DiagLink_ResetFrame(context);
    return;
  }

  if (context->rx_length == 0U)
  {
    return;
  }

  if ((HAL_GetTick() - context->last_rx_tick) < context->frame_gap_ms)
  {
    return;
  }

  context->stats.rx_frames++;
  context->stats.last_request_length = context->rx_length;
  context->stats.last_response_length = 0U;

  if (context->handler != NULL)
  {
    response_length = context->handler(
      context->rx_buffer,
      context->rx_length,
      context->tx_buffer,
      DIAG_LINK_TX_BUFFER_SIZE,
      context->handler_user_context);
  }

  if (response_length > 0U)
  {
    (void)HAL_UART_Transmit(context->uart, context->tx_buffer, response_length, HAL_MAX_DELAY);
    context->stats.tx_frames++;
    context->stats.tx_bytes += response_length;
    context->stats.last_response_length = response_length;
  }

  DiagLink_ResetFrame(context);
}

void DiagLink_HandleRxComplete(DiagLinkContext *context, UART_HandleTypeDef *huart)
{
  if ((context == NULL) || (huart != context->uart))
  {
    return;
  }

  context->stats.rx_bytes++;
  context->last_rx_tick = HAL_GetTick();

  if (context->frame_overflow == 0U)
  {
    if (context->rx_length < DIAG_LINK_RX_BUFFER_SIZE)
    {
      context->rx_buffer[context->rx_length++] = context->rx_byte;
    }
    else
    {
      context->frame_overflow = 1U;
      context->stats.dropped_frames++;
    }
  }

  (void)DiagLink_ArmReceive(context);
}

void DiagLink_HandleError(DiagLinkContext *context, UART_HandleTypeDef *huart)
{
  if ((context == NULL) || (huart != context->uart))
  {
    return;
  }

  context->stats.uart_errors++;
  context->uart_error_pending = 1U;
  __HAL_UART_CLEAR_OREFLAG(huart);
  __HAL_UART_CLEAR_NEFLAG(huart);
  __HAL_UART_CLEAR_FEFLAG(huart);
  __HAL_UART_CLEAR_PEFLAG(huart);
  (void)DiagLink_ArmReceive(context);
}

void DiagLink_GetStats(const DiagLinkContext *context, DiagLinkStats *stats)
{
  if (stats == NULL)
  {
    return;
  }

  if (context == NULL)
  {
    memset(stats, 0, sizeof(*stats));
    return;
  }

  *stats = context->stats;
}

static HAL_StatusTypeDef DiagLink_ArmReceive(DiagLinkContext *context)
{
  return HAL_UART_Receive_IT(context->uart, &context->rx_byte, 1U);
}

static void DiagLink_ResetFrame(DiagLinkContext *context)
{
  context->rx_length = 0U;
}
