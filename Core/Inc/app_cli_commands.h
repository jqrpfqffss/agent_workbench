#ifndef __APP_CLI_COMMANDS_H
#define __APP_CLI_COMMANDS_H

#include "cli.h"

#ifdef __cplusplus
extern "C" {
#endif

const CliCommand *AppCli_GetCommands(size_t *count);

#ifdef __cplusplus
}
#endif

#endif /* __APP_CLI_COMMANDS_H */
