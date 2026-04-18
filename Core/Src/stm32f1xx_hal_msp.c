/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file         stm32f1xx_hal_msp.c
  * @brief        This file provides code for the MSP Initialization
  *               and de-Initialization codes.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2025 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Includes ------------------------------------------------------------------*/
#include "main.h"
/* USER CODE BEGIN Includes */
#include "app_serial_config.h"

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN TD */

/* USER CODE END TD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN Define */

/* USER CODE END Define */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN Macro */

/* USER CODE END Macro */

/* Private variables ---------------------------------------------------------*/
/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* External functions --------------------------------------------------------*/
/* USER CODE BEGIN ExternalFunctions */

/* USER CODE END ExternalFunctions */

/* USER CODE BEGIN 0 */

/* USER CODE END 0 */
/**
  * Initializes the Global MSP.
  */
void HAL_MspInit(void)
{

  /* USER CODE BEGIN MspInit 0 */

  /* USER CODE END MspInit 0 */

  __HAL_RCC_AFIO_CLK_ENABLE();
  __HAL_RCC_PWR_CLK_ENABLE();

  /* System interrupt init*/

  /** NOJTAG: JTAG-DP Disabled and SW-DP Enabled
  */
  __HAL_AFIO_REMAP_SWJ_NOJTAG();

  /* USER CODE BEGIN MspInit 1 */

  /* USER CODE END MspInit 1 */
}

/**
  * @brief UART MSP Initialization
  * This function configures the hardware resources used in this example
  * @param huart: UART handle pointer
  * @retval None
  */
void HAL_UART_MspInit(UART_HandleTypeDef* huart)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  if(huart->Instance==APP_DIAG_UART_INSTANCE)
  {
    /* USER CODE BEGIN USART1_MspInit 0 */

    /* USER CODE END USART1_MspInit 0 */
    APP_DIAG_UART_CLK_ENABLE();

    APP_DIAG_UART_GPIO_CLK_ENABLE();
    GPIO_InitStruct.Pin = APP_DIAG_UART_TX_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(APP_DIAG_UART_TX_GPIO_PORT, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = APP_DIAG_UART_RX_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(APP_DIAG_UART_RX_GPIO_PORT, &GPIO_InitStruct);

    HAL_NVIC_SetPriority(APP_DIAG_UART_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(APP_DIAG_UART_IRQn);
    /* USER CODE BEGIN USART1_MspInit 1 */

    /* USER CODE END USART1_MspInit 1 */
  }
  else if(huart->Instance==APP_DEBUG_UART_INSTANCE)
  {
    /* USER CODE BEGIN USART2_MspInit 0 */

    /* USER CODE END USART2_MspInit 0 */
    /* Peripheral clock enable */
    APP_DEBUG_UART_CLK_ENABLE();

    APP_DEBUG_UART_GPIO_CLK_ENABLE();
    GPIO_InitStruct.Pin = APP_DEBUG_UART_TX_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(APP_DEBUG_UART_TX_GPIO_PORT, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = APP_DEBUG_UART_RX_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(APP_DEBUG_UART_RX_GPIO_PORT, &GPIO_InitStruct);

    /* USART2 interrupt Init */
    HAL_NVIC_SetPriority(APP_DEBUG_UART_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(APP_DEBUG_UART_IRQn);
    /* USER CODE BEGIN USART2_MspInit 1 */

    /* USER CODE END USART2_MspInit 1 */

  }

}

/**
  * @brief UART MSP De-Initialization
  * This function freeze the hardware resources used in this example
  * @param huart: UART handle pointer
  * @retval None
  */
void HAL_UART_MspDeInit(UART_HandleTypeDef* huart)
{
  if(huart->Instance==APP_DIAG_UART_INSTANCE)
  {
    /* USER CODE BEGIN USART1_MspDeInit 0 */

    /* USER CODE END USART1_MspDeInit 0 */
    APP_DIAG_UART_CLK_DISABLE();

    HAL_GPIO_DeInit(APP_DIAG_UART_TX_GPIO_PORT, APP_DIAG_UART_TX_PIN);
    HAL_GPIO_DeInit(APP_DIAG_UART_RX_GPIO_PORT, APP_DIAG_UART_RX_PIN);

    HAL_NVIC_DisableIRQ(APP_DIAG_UART_IRQn);
    /* USER CODE BEGIN USART1_MspDeInit 1 */

    /* USER CODE END USART1_MspDeInit 1 */
  }
  else if(huart->Instance==APP_DEBUG_UART_INSTANCE)
  {
    /* USER CODE BEGIN USART2_MspDeInit 0 */

    /* USER CODE END USART2_MspDeInit 0 */
    /* Peripheral clock disable */
    APP_DEBUG_UART_CLK_DISABLE();

    HAL_GPIO_DeInit(APP_DEBUG_UART_TX_GPIO_PORT, APP_DEBUG_UART_TX_PIN);
    HAL_GPIO_DeInit(APP_DEBUG_UART_RX_GPIO_PORT, APP_DEBUG_UART_RX_PIN);

    /* USART2 interrupt DeInit */
    HAL_NVIC_DisableIRQ(APP_DEBUG_UART_IRQn);
    /* USER CODE BEGIN USART2_MspDeInit 1 */

    /* USER CODE END USART2_MspDeInit 1 */
  }

}

/* USER CODE BEGIN 1 */

/* USER CODE END 1 */
