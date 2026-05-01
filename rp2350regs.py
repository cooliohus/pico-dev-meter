
#    K3JSE Pico based deviation meter RP2350 register definitions
#    Copyright (C) 2026  W. Andy Cooper, K3JSE
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#    The author can be contacted by email at k3jse@coolioh.com#




# https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf

# GPIO Functi#ons Page 12
# GPIO Registers page 244


GPIO_BASE       = 0x40028000   # IO_BANK0_BASE Page 32
GPIO_CHAN_WIDTH = 0x08
GPIO_PIN_COUNT  = 30
PAD_BASE        = 0x40038000
PAD_PIN_WIDTH   = 0x04

PPB_BASE        = 0xe0000000

########## DMA Defines ##########
#
#  DMA Description starts at page 91
#  Page 101
#
#  - The basic set, does not [yet] include aliasing, chaining, ring, and interrupt stuff
#  - Transfer count is the number of transfer, not the number of bytes set by the CTRL Register
 
DMA_BASE        = 0x50000000
DMA_CHAN_WIDTH  = 0x40
DMA_CHAN_COUNT  = 16

# DMA Channel Registers 0ne per channel relative to DMA_BASE (RP2350 pg 1096)
DMA_CH_READ_ADDR    = 0x00
DMA_CH_WRITE_ADDR   = 0x04
DMA_CH_TRANS_COUNT  = 0x08
DMA_CH_CTRL         = 0x0C

########## DMA CTRL Register Defines (RP2350 pg 1127) ##########
DMA_BIT_AHB_ERROR      = 31
DMA_BIT_READ_ERROR     = 30
DMA_BIT_WRITE_ERROR    = 29
DMA_RESERVED           =27
DMA_BIT_BUSY           = 26
DMA_BIT_SNIFF_EN       = 25
DMA_BIT_BSWP           = 24
DMA_BIT_IRQ_QUIET      = 23
DMA_BIT_TREQ_SEL       = 17
DMA_CHAIN_TO           = 13
DMA_BIT_RING_SELECT    = 12
DMA_BIT_RING_SIZE      = 8
DMA_BIT_INCR_WRITE_REV = 7
DMA_BIT_INCR_WRITE     = 6
DMA_BIT_INCR_READ_REV  = 5
DMA_BIT_INCR_READ      = 4
DMA_BIT_DATA_SIZE     = 2
DMA_BIT_HIGH_PRIOR  = 1
DMA_BIT_EN          = 0

# See pg 95 for DREQ channels
DREQ_ADC = 48


# Page 1101
#DREQ DREQ Channel DREQ DREQ Channel DREQ DREQ Channel DREQ DREQ Channel
#0 DREQ_PIO0_TX0 14 DREQ_PIO1_RX2 28 DREQ_UART0_TX 42 DREQ_PWM_WRAP10
#1 DREQ_PIO0_TX1 15 DREQ_PIO1_RX3 29 DREQ_UART0_RX 43 DREQ_PWM_WRAP11
#2 DREQ_PIO0_TX2 16 DREQ_PIO2_TX0 30 DREQ_UART1_TX 44 DREQ_I2C0_TX
#3 DREQ_PIO0_TX3 17 DREQ_PIO2_TX1 31 DREQ_UART1_RX 45 DREQ_I2C0_RX
#4 DREQ_PIO0_RX0 18 DREQ_PIO2_TX2 32 DREQ_PWM_WRAP0 46 DREQ_I2C1_TX
#5 DREQ_PIO0_RX1 19 DREQ_PIO2_TX3 33 DREQ_PWM_WRAP1 47 DREQ_I2C1_RX
#6 DREQ_PIO0_RX2 20 DREQ_PIO2_RX0 34 DREQ_PWM_WRAP2 48 DREQ_ADC
#7 DREQ_PIO0_RX3 21 DREQ_PIO2_RX1 35 DREQ_PWM_WRAP3 49 DREQ_XIP_STREAM
#8 DREQ_PIO1_TX0 22 DREQ_PIO2_RX2 36 DREQ_PWM_WRAP4 50 DREQ_XIP_QMITX
#9 DREQ_PIO1_TX1 23 DREQ_PIO2_RX3 37 DREQ_PWM_WRAP5 51 DREQ_XIP_QMIRX
#10 DREQ_PIO1_TX2 24 DREQ_SPI0_TX 38 DREQ_PWM_WRAP6 52 DREQ_HSTX
#11 DREQ_PIO1_TX3 25 DREQ_SPI0_RX 39 DREQ_PWM_WRAP7 53 DREQ_CORESIGHT
#12 DREQ_PIO1_RX0 26 DREQ_SPI1_TX 40 DREQ_PWM_WRAP8 54 DREQ_SHA256
#13 DREQ_PIO1_RX1 27 DREQ_SPI1_RX 41 DREQ_PWM_WRAP




# Selected ADC-CH_CTRL defines (pg 112)
ADC_CTRL_BUSY       = 24
ADC_CTRL_TR_SEL     = 15		# See pg 95 for DREQ channels (above)
ADC_CTRL_INC_WRITE  = 5
ADC_CTRL_INC_READ   = 4
ADC_CTRL_DATA_SIZE  = 2
ADC_CTRL_EN         = 0

########## ADC Register Defines (pg 563) ##########
ADC_BASE            = 0x400A0000
ADC_CS              = 0x00
ADC_RSLT            = 0x04
ADC_FCS             = 0x08
ADC_FIFO            = 0x0C
ADC_DIV             = 0x10

# ADC CS Register Offset Defines (pg 564)
ADC_BIT_RROBIN      = 16   #:20
ADC_BIT_AINSEL      = 12   #:14
ADC_BIT_ERR_STICKY  = 10
ADC_BIT_ERR         = 9
ADC_BIT_READY       = 8
ADC_BIT_START_MANY  = 3
ADC_BIT_START_ONCE  = 2
ADC_BIT_TS_EN       = 1
ADC_BIT_EN          = 0   # Power on ADC and enable clock

# ADC FCS Register Offset Defines (pg 564)
FCS_BIT_THRESH      = 24   #:27
FCS_BIT_LEVEL       = 16   #:19
FCS_BIT_OVER        = 11   # write 1 to clear
FCS_BIT_UNDER       = 10   # write 1 to clear
FCS_BIT_FULL        = 9
FCS_BIT_EMPTY       = 8
FCS_BIT_DREQEN      = 3
FCS_BIT_ERR         = 2
FCS_BIT_SHIFT       = 1
FCS_BIT_EN          = 0

# ADC FIFO Register Offset Defines (pg 565)
ADC_BIT_ERR         = 15
ADC_BIT_VAL         = 0

# ADC DIV Register Offset Defines (pg 565)
ADC_DIV_INT         = 8
ADC_DIV_FRAC        = 0


########## SIO Defines ##########
SIO_BASE            = 0xd0000000
SIO_LEN             = 0x180
CPUID               = 0x00
GPIO_IN             = 0x04
GPIO_OUT            = 0x10
GPIO_HI_OUT         = 0x14
GPIO_OUT_SET        = 0x18
GPIO_HI_OUT_SET     = 0x1C
GPIO_OUT_CLR        = 0x20
GPIO_HI_OUT_CLR     = 0x24
GPIO_OUT_XOR        = 0x28
GPIO_HI_OUT_XOR     = 0x2C
GPIO_OE             = 0x30
GPIO_HI_OE          = 0x34
GPIO_OE_SET         = 0x38
GPIO_HI_OE_SET      = 0x3C
GPIO_OE_CLR         = 0x40
GPIO_HI_OE_CLR      = 0x44
GPIO_OE_XOR         = 0x48
GPIO_HI_OE_XOR      = 0x4C