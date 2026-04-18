#ifndef __APP_DIAG_MODBUS_H
#define __APP_DIAG_MODBUS_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define APP_DIAG_MB_FUNC_READ_HOLDING_REGISTERS 0x03U
#define APP_DIAG_MB_FUNC_WRITE_SINGLE_REGISTER 0x06U

#define APP_DIAG_MB_REG_PROTOCOL_VERSION 0x0000U
#define APP_DIAG_MB_REG_SLAVE_ADDRESS 0x0001U
#define APP_DIAG_MB_REG_LED_RED 0x0010U
#define APP_DIAG_MB_REG_LED_GREEN 0x0011U
#define APP_DIAG_MB_REG_LED_BLUE 0x0012U
#define APP_DIAG_MB_REG_REQUEST_OK_COUNT 0x0020U
#define APP_DIAG_MB_REG_EXCEPTION_COUNT 0x0021U
#define APP_DIAG_MB_REG_CRC_ERROR_COUNT 0x0022U

typedef struct
{
  uint8_t slave_address;
  uint32_t handled_requests;
  uint32_t ignored_frames;
  uint32_t crc_errors;
  uint32_t exception_responses;
  uint8_t last_function;
  uint8_t last_exception;
  uint16_t last_register;
  uint16_t last_argument;
} AppDiagModbusState;

typedef struct
{
  AppDiagModbusState state;
} AppDiagModbusContext;

void AppDiagModbus_Init(AppDiagModbusContext *context, uint8_t slave_address);
uint16_t AppDiagModbus_HandleRequest(
  const uint8_t *request,
  uint16_t request_length,
  uint8_t *response,
  uint16_t response_capacity,
  void *user_context);
void AppDiagModbus_GetState(const AppDiagModbusContext *context, AppDiagModbusState *state);

#ifdef __cplusplus
}
#endif

#endif /* __APP_DIAG_MODBUS_H */
