#ifndef __APP_RUNTIME_H
#define __APP_RUNTIME_H

#include "app_diag_modbus.h"
#include "cli.h"
#include "diag_link.h"

#ifdef __cplusplus
extern "C" {
#endif

extern CliContext g_debug_cli;
extern DiagLinkContext g_diag_link;
extern AppDiagModbusContext g_diag_modbus;

#ifdef __cplusplus
}
#endif

#endif /* __APP_RUNTIME_H */
