cmake_minimum_required(VERSION 3.20)

if(NOT CMAKE_TOOLCHAIN_FILE AND NOT DEFINED CMAKE_C_COMPILER)
  include("${CMAKE_CURRENT_LIST_DIR}/cmake/arm-none-eabi-toolchain.cmake")
endif()

project(serial LANGUAGES C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

foreach(config DEBUG RELEASE RELWITHDEBINFO MINSIZEREL)
  set(CMAKE_C_FLAGS_${config} "" CACHE STRING "" FORCE)
  set(CMAKE_ASM_FLAGS_${config} "" CACHE STRING "" FORCE)
  set(CMAKE_EXE_LINKER_FLAGS_${config} "" CACHE STRING "" FORCE)
endforeach()

if(NOT CMAKE_C_COMPILER MATCHES "arm-none-eabi")
  message(FATAL_ERROR "This project must be built with the Arm GNU toolchain. Use CMakePresets.json or pass -DCMAKE_TOOLCHAIN_FILE=cmake/arm-none-eabi-toolchain.cmake.")
endif()

set(MCU_FLAGS
  -mcpu=cortex-m3
  -mthumb
  -mfloat-abi=soft
)

set(LINKER_SCRIPT_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/STM32F103C8TX_FLASH.ld")
set(LINKER_SCRIPT "${LINKER_SCRIPT_SOURCE}")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${LINKER_SCRIPT_SOURCE}")

if(CMAKE_C_COMPILER_ID STREQUAL "GNU" AND CMAKE_C_COMPILER_VERSION VERSION_LESS 11.0)
  file(READ "${LINKER_SCRIPT_SOURCE}" LINKER_SCRIPT_CONTENT)
  string(REPLACE "(READONLY)" "" LINKER_SCRIPT_CONTENT "${LINKER_SCRIPT_CONTENT}")
  set(LINKER_SCRIPT "${CMAKE_CURRENT_BINARY_DIR}/STM32F103C8TX_FLASH.ld")
  file(WRITE "${LINKER_SCRIPT}" "${LINKER_SCRIPT_CONTENT}")
endif()

set(PROJECT_SOURCES
  Core/Src/main.c
  Core/Src/cli.c
  Core/Src/app_cli_commands.c
  Core/Src/stm32f1xx_hal_msp.c
  Core/Src/stm32f1xx_it.c
  Core/Src/syscalls.c
  Core/Src/sysmem.c
  Core/Src/system_stm32f1xx.c
  Core/Startup/startup_stm32f103c8tx.s
  Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal.c
  Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_cortex.c
  Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_dma.c
  Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_exti.c
  Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_flash.c
  Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_flash_ex.c
  Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_gpio.c
  Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_gpio_ex.c
  Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_pwr.c
  Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_rcc.c
  Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_rcc_ex.c
  Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_uart.c
)

add_executable(${PROJECT_NAME} ${PROJECT_SOURCES})

set_target_properties(${PROJECT_NAME} PROPERTIES
  SUFFIX ".elf"
)

target_include_directories(${PROJECT_NAME} PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/Core/Inc
  ${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F1xx_HAL_Driver/Inc
  ${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F1xx_HAL_Driver/Inc/Legacy
  ${CMAKE_CURRENT_SOURCE_DIR}/Drivers/CMSIS/Device/ST/STM32F1xx/Include
  ${CMAKE_CURRENT_SOURCE_DIR}/Drivers/CMSIS/Include
)

target_compile_definitions(${PROJECT_NAME} PRIVATE
  USE_HAL_DRIVER
  STM32F103xB
  $<$<CONFIG:Debug>:DEBUG>
)

target_compile_options(${PROJECT_NAME} PRIVATE
  ${MCU_FLAGS}
  --specs=nano.specs
  $<$<COMPILE_LANGUAGE:C>:-ffunction-sections>
  $<$<COMPILE_LANGUAGE:C>:-fdata-sections>
  $<$<COMPILE_LANGUAGE:C>:-Wall>
  $<$<COMPILE_LANGUAGE:ASM>:-x$<SEMICOLON>assembler-with-cpp>
  $<$<CONFIG:Debug>:-g3>
  $<$<CONFIG:Debug>:-O0>
  $<$<AND:$<CONFIG:Debug>,$<COMPILE_LANGUAGE:C>>:-fstack-usage>
  $<$<CONFIG:Release>:-g0>
  $<$<CONFIG:Release>:-Os>
)

if(CMAKE_C_COMPILER_ID STREQUAL "GNU" AND CMAKE_C_COMPILER_VERSION VERSION_GREATER_EQUAL 13.0)
  target_compile_options(${PROJECT_NAME} PRIVATE
    $<$<AND:$<CONFIG:Debug>,$<COMPILE_LANGUAGE:C>>:-fcyclomatic-complexity>
  )
endif()

target_link_options(${PROJECT_NAME} PRIVATE
  ${MCU_FLAGS}
  -T${LINKER_SCRIPT}
  --specs=nosys.specs
  --specs=nano.specs
  -Wl,-Map=${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}.map
  -Wl,--gc-sections
  -static
  -Wl,--start-group
  -lc
  -lm
  -Wl,--end-group
)

if(CMAKE_OBJCOPY)
  add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:${PROJECT_NAME}> ${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:${PROJECT_NAME}> ${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}.bin
    VERBATIM
  )
endif()

if(CMAKE_SIZE)
  add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:${PROJECT_NAME}>
    VERBATIM
  )
endif()
