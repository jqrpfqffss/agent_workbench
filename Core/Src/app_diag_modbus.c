#include "app_diag_modbus.h"

#include "main.h"

#include <string.h>

#define APP_DIAG_MB_PROTOCOL_VERSION 0x0100U
#define APP_DIAG_MB_EXCEPTION_ILLEGAL_FUNCTION 0x01U
#define APP_DIAG_MB_EXCEPTION_ILLEGAL_DATA_ADDRESS 0x02U
#define APP_DIAG_MB_EXCEPTION_ILLEGAL_DATA_VALUE 0x03U

static uint16_t AppDiagModbus_Crc16(const uint8_t *data, uint16_t length);
static uint16_t AppDiagModbus_BuildException(
  AppDiagModbusContext *context,
  uint8_t address,
  uint8_t function,
  uint8_t exception_code,
  uint8_t *response,
  uint16_t response_capacity);
static uint8_t AppDiagModbus_ReadRegister(AppDiagModbusContext *context, uint16_t address, uint16_t *value);
static uint8_t AppDiagModbus_WriteRegister(uint16_t address, uint16_t value);
static uint16_t AppDiagModbus_ReadRegisters(
  AppDiagModbusContext *context,
  uint8_t address,
  uint16_t start_register,
  uint16_t quantity,
  uint8_t *response,
  uint16_t response_capacity);
static uint16_t AppDiagModbus_WriteSingleRegister(
  AppDiagModbusContext *context,
  uint8_t address,
  uint16_t register_address,
  uint16_t register_value,
  uint8_t *response,
  uint16_t response_capacity);

void AppDiagModbus_Init(AppDiagModbusContext *context, uint8_t slave_address)
{
  memset(context, 0, sizeof(*context));
  context->state.slave_address = slave_address;
}

uint16_t AppDiagModbus_HandleRequest(
  const uint8_t *request,
  uint16_t request_length,
  uint8_t *response,
  uint16_t response_capacity,
  void *user_context)
{
  AppDiagModbusContext *context = (AppDiagModbusContext *)user_context;
  uint16_t request_crc = 0U;
  uint16_t computed_crc = 0U;
  uint8_t address = 0U;
  uint8_t function = 0U;
  uint16_t register_address = 0U;
  uint16_t argument = 0U;

  if ((context == NULL) || (request == NULL) || (response == NULL) || (request_length < 4U))
  {
    return 0U;
  }

  address = request[0];
  function = request[1];
  context->state.last_function = function;
  context->state.last_exception = 0U;

  if (address != context->state.slave_address)
  {
    context->state.ignored_frames++;
    return 0U;
  }

  request_crc = (uint16_t)request[request_length - 2U] | ((uint16_t)request[request_length - 1U] << 8U);
  computed_crc = AppDiagModbus_Crc16(request, (uint16_t)(request_length - 2U));
  if (request_crc != computed_crc)
  {
    context->state.crc_errors++;
    return 0U;
  }

  if (request_length != 8U)
  {
    return AppDiagModbus_BuildException(
      context,
      address,
      function,
      APP_DIAG_MB_EXCEPTION_ILLEGAL_DATA_VALUE,
      response,
      response_capacity);
  }

  register_address = (uint16_t)((request[2] << 8U) | request[3]);
  argument = (uint16_t)((request[4] << 8U) | request[5]);
  context->state.last_register = register_address;
  context->state.last_argument = argument;
  context->state.handled_requests++;

  switch (function)
  {
    case APP_DIAG_MB_FUNC_READ_HOLDING_REGISTERS:
      return AppDiagModbus_ReadRegisters(
        context,
        address,
        register_address,
        argument,
        response,
        response_capacity);

    case APP_DIAG_MB_FUNC_WRITE_SINGLE_REGISTER:
      return AppDiagModbus_WriteSingleRegister(
        context,
        address,
        register_address,
        argument,
        response,
        response_capacity);

    default:
      return AppDiagModbus_BuildException(
        context,
        address,
        function,
        APP_DIAG_MB_EXCEPTION_ILLEGAL_FUNCTION,
        response,
        response_capacity);
  }
}

void AppDiagModbus_GetState(const AppDiagModbusContext *context, AppDiagModbusState *state)
{
  if (state == NULL)
  {
    return;
  }

  if (context == NULL)
  {
    memset(state, 0, sizeof(*state));
    return;
  }

  *state = context->state;
}

static uint16_t AppDiagModbus_Crc16(const uint8_t *data, uint16_t length)
{
  uint16_t crc = 0xFFFFU;
  uint16_t index = 0U;
  uint8_t bit = 0U;

  for (index = 0U; index < length; ++index)
  {
    crc ^= data[index];
    for (bit = 0U; bit < 8U; ++bit)
    {
      if ((crc & 0x0001U) != 0U)
      {
        crc = (uint16_t)((crc >> 1U) ^ 0xA001U);
      }
      else
      {
        crc >>= 1U;
      }
    }
  }

  return crc;
}

static uint16_t AppDiagModbus_BuildException(
  AppDiagModbusContext *context,
  uint8_t address,
  uint8_t function,
  uint8_t exception_code,
  uint8_t *response,
  uint16_t response_capacity)
{
  uint16_t crc = 0U;

  if (response_capacity < 5U)
  {
    return 0U;
  }

  response[0] = address;
  response[1] = (uint8_t)(function | 0x80U);
  response[2] = exception_code;
  crc = AppDiagModbus_Crc16(response, 3U);
  response[3] = (uint8_t)(crc & 0x00FFU);
  response[4] = (uint8_t)(crc >> 8U);
  context->state.last_exception = exception_code;
  context->state.exception_responses++;
  return 5U;
}

static uint8_t AppDiagModbus_ReadRegister(AppDiagModbusContext *context, uint16_t address, uint16_t *value)
{
  if ((context == NULL) || (value == NULL))
  {
    return 0U;
  }

  switch (address)
  {
    case APP_DIAG_MB_REG_PROTOCOL_VERSION:
      *value = APP_DIAG_MB_PROTOCOL_VERSION;
      return 1U;

    case APP_DIAG_MB_REG_SLAVE_ADDRESS:
      *value = context->state.slave_address;
      return 1U;

    case APP_DIAG_MB_REG_LED_RED:
      *value = (HAL_GPIO_ReadPin(LED_RED_GPIO_Port, LED_RED_Pin) == GPIO_PIN_SET) ? 1U : 0U;
      return 1U;

    case APP_DIAG_MB_REG_LED_GREEN:
      *value = (HAL_GPIO_ReadPin(LED_GREEN_GPIO_Port, LED_GREEN_Pin) == GPIO_PIN_SET) ? 1U : 0U;
      return 1U;

    case APP_DIAG_MB_REG_LED_BLUE:
      *value = (HAL_GPIO_ReadPin(LED_BLUE_GPIO_Port, LED_BLUE_Pin) == GPIO_PIN_SET) ? 1U : 0U;
      return 1U;

    case APP_DIAG_MB_REG_REQUEST_OK_COUNT:
      *value = (uint16_t)(context->state.handled_requests & 0xFFFFU);
      return 1U;

    case APP_DIAG_MB_REG_EXCEPTION_COUNT:
      *value = (uint16_t)(context->state.exception_responses & 0xFFFFU);
      return 1U;

    case APP_DIAG_MB_REG_CRC_ERROR_COUNT:
      *value = (uint16_t)(context->state.crc_errors & 0xFFFFU);
      return 1U;

    default:
      return 0U;
  }
}

static uint8_t AppDiagModbus_WriteRegister(uint16_t address, uint16_t value)
{
  if (value > 1U)
  {
    return APP_DIAG_MB_EXCEPTION_ILLEGAL_DATA_VALUE;
  }

  switch (address)
  {
    case APP_DIAG_MB_REG_LED_RED:
      HAL_GPIO_WritePin(LED_RED_GPIO_Port, LED_RED_Pin, (value != 0U) ? GPIO_PIN_SET : GPIO_PIN_RESET);
      return 0U;

    case APP_DIAG_MB_REG_LED_GREEN:
      HAL_GPIO_WritePin(LED_GREEN_GPIO_Port, LED_GREEN_Pin, (value != 0U) ? GPIO_PIN_SET : GPIO_PIN_RESET);
      return 0U;

    case APP_DIAG_MB_REG_LED_BLUE:
      HAL_GPIO_WritePin(LED_BLUE_GPIO_Port, LED_BLUE_Pin, (value != 0U) ? GPIO_PIN_SET : GPIO_PIN_RESET);
      return 0U;

    default:
      return APP_DIAG_MB_EXCEPTION_ILLEGAL_DATA_ADDRESS;
  }
}

static uint16_t AppDiagModbus_ReadRegisters(
  AppDiagModbusContext *context,
  uint8_t address,
  uint16_t start_register,
  uint16_t quantity,
  uint8_t *response,
  uint16_t response_capacity)
{
  uint16_t crc = 0U;
  uint16_t response_length = 0U;
  uint16_t value = 0U;
  uint16_t index = 0U;

  if ((quantity == 0U) || (quantity > 16U))
  {
    return AppDiagModbus_BuildException(
      context,
      address,
      APP_DIAG_MB_FUNC_READ_HOLDING_REGISTERS,
      APP_DIAG_MB_EXCEPTION_ILLEGAL_DATA_VALUE,
      response,
      response_capacity);
  }

  response_length = (uint16_t)(5U + (quantity * 2U));
  if (response_capacity < response_length)
  {
    return 0U;
  }

  response[0] = address;
  response[1] = APP_DIAG_MB_FUNC_READ_HOLDING_REGISTERS;
  response[2] = (uint8_t)(quantity * 2U);

  for (index = 0U; index < quantity; ++index)
  {
    if (AppDiagModbus_ReadRegister(context, (uint16_t)(start_register + index), &value) == 0U)
    {
      return AppDiagModbus_BuildException(
        context,
        address,
        APP_DIAG_MB_FUNC_READ_HOLDING_REGISTERS,
        APP_DIAG_MB_EXCEPTION_ILLEGAL_DATA_ADDRESS,
        response,
        response_capacity);
    }

    response[3U + (index * 2U)] = (uint8_t)(value >> 8U);
    response[4U + (index * 2U)] = (uint8_t)(value & 0x00FFU);
  }

  crc = AppDiagModbus_Crc16(response, (uint16_t)(response_length - 2U));
  response[response_length - 2U] = (uint8_t)(crc & 0x00FFU);
  response[response_length - 1U] = (uint8_t)(crc >> 8U);
  return response_length;
}

static uint16_t AppDiagModbus_WriteSingleRegister(
  AppDiagModbusContext *context,
  uint8_t address,
  uint16_t register_address,
  uint16_t register_value,
  uint8_t *response,
  uint16_t response_capacity)
{
  uint8_t write_status = 0U;
  uint16_t crc = 0U;

  if (response_capacity < 8U)
  {
    return 0U;
  }

  write_status = AppDiagModbus_WriteRegister(register_address, register_value);
  if (write_status != 0U)
  {
    return AppDiagModbus_BuildException(
      context,
      address,
      APP_DIAG_MB_FUNC_WRITE_SINGLE_REGISTER,
      write_status,
      response,
      response_capacity);
  }

  response[0] = address;
  response[1] = APP_DIAG_MB_FUNC_WRITE_SINGLE_REGISTER;
  response[2] = (uint8_t)(register_address >> 8U);
  response[3] = (uint8_t)(register_address & 0x00FFU);
  response[4] = (uint8_t)(register_value >> 8U);
  response[5] = (uint8_t)(register_value & 0x00FFU);
  crc = AppDiagModbus_Crc16(response, 6U);
  response[6] = (uint8_t)(crc & 0x00FFU);
  response[7] = (uint8_t)(crc >> 8U);
  return 8U;
}
