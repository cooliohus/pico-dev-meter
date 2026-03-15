import uctypes, time, array, sys
from machine import mem32,mem16, mem8, ADC, Pin, I2C

#import framebuf
from ssd1306 import SSD1306_I2C
import onewire
#import rp2, select
#import serial
#ser = serial.Serial("/dev/ttyACM1")
#print(ser.name)

# https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf

# GPIO Functions Page 12
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

###############################################################################
# Initialize the SSD1306 OLED display if present.
#
# The variable have_oled is set to false if there is no display present and the
# display routines will not attempt to update (a non-existant display)
#
pix_res_x = 128  # SSD1306 horizontal resolution
pix_res_y = 64   # SSD1306 vertical resolution

i2c_dev = I2C(0,scl=Pin(21),sda=Pin(20),freq=200000)  # start I2C on I2C1 (GPIO 26/27)
i2c_addr = [hex(ii) for ii in i2c_dev.scan()]         # get I2C address in hex format
if i2c_addr==[]:
    print('No I2C Display Found') 
    have_oled = False
    #sys.exit() # exit routine if no dev found
else:
    print("I2C Address      : {}".format(i2c_addr[0])) # I2C device address
    print("I2C Configuration: {}".format(i2c_dev))     # print I2C params
    oled = SSD1306_I2C(pix_res_x, pix_res_y, i2c_dev)  # oled controller
    have_oled = True



#######################################################
#
# Some global stuff
#
#######################################################

DEBUG = False           # print debug abd timing information

ADC_SHIFT   = False     # Select 8 bit or 12 bit ADC DMA transfers. True = 8 bit
ADC_PIN     = 26
ADC_RATE    = 75_000    # ADC sample rate
ADC_SAMPLES = 5_000    # Number of samples for DMA count

if ADC_SHIFT:           # Set maximum ADC count based on DMA shift
    ADC_MAX = 255
else:
    ADC_MAX = 4095

dma0 = DMA_BASE                                       # Select DMA0

# Declare ADC buffer global to avoide allocation overhead
if ADC_SHIFT:     # byte size buffer
    adc_buffer = array.array('B', (0 for _ in range(ADC_SAMPLES)))   # DMA buffer for ADC, 'B' = bytes
else:             # ushort (two byte) buffer
    adc_buffer = array.array('H', (0 for _ in range(ADC_SAMPLES)))  # DMA buffer for ADC, 'H' = ushort, two bytes

adc_init = ADC(Pin(ADC_PIN))                    # initialize ADC Pin
mem32[ADC_BASE+ADC_CS] = 1                      # Power on ADC

#led_pin = 13  # Metro
led_pin = 25  # Pico
led = Pin(led_pin,Pin.OUT)
ledmask = 1<<led_pin

#######################################################
#
# End of global stuff
#
#######################################################



def update_display(dev): #audio,dev, freq):
    if have_oled:
        s1 = '{:>4}'.format(dev)
        oled.fill(0) # clear screen
        oled.fill_rect(0, 0, 127, 63, 1) # build big border
        oled.fill_rect(2, 2, 124, 60, 0)
        oled.text("Deviation:",25,15)
        oled.text(" "+ s1 + " Hz.",20,30)
        oled.show() # show new text

def blink_led():
    # create a python integer from a four byte memory slice at offset (pin# * 8) as each pin has a
    # four byte status register and four byte control register.  "+4" steps over the status register
    if DEBUG:
        d32 = mem32[GPIO_BASE+led_pin*8+4]
        print('GPIO',led_pin,'ctrl register (pg 243,247:',hex(d32),bin(d32))
        d32 = mem32[PAD_BASE+led_pin*8+4] 
        print('GPIO',led_pin,'pad register (pg 299,300):',hex(d32),bin(d32))
    
        # Display gpio output enable register - bit 13 or 25 should be set
        # "sio" is what RP2040 calls digital io
        oe = mem32[SIO_BASE+led_pin*8+4] 
        print('GPIO Output Enable (pg 42 and on), :',hex(oe),bin(oe))

    #for _ in range(5):
    #    mem32[SIO_BASE+GPIO_OUT_SET] = ledmask
    #    time.sleep(1)
    #    mem32[SIO_BASE+GPIO_OUT_CLR] = ledmask
    #    time.sleep(1)
    mem32[SIO_BASE+GPIO_OUT_XOR] = ledmask

def adc_read_1_dbg(adc) -> int:
    # Get one DMA sample
    cs = mem32[adc+ADC_CS]
    if DEBUG:
        print("CS:",bin(cs))
    #cs = 0
    cs =  (1 << ADC_BIT_START_ONCE | 1 << ADC_BIT_EN)     # start one adc sample
    mem32[adc+ADC_CS] = cs
    while True:                                           # wait for adc complete
        cs = mem32[adc+ADC_CS]                            # fetch status register
        if cs & (1 << ADC_BIT_READY) > 1:                 # check for result ready
            break
    cs = mem32[adc+ADC_CS]                                # fetch and print status
    #print('ADC CS (pg 563), :',hex(cs),bin(cs))        
    cs = mem32[adc+ADC_RSLT]                              # fetch and print adc result
    #mem32[adc+ADC_CS] =  1 << ADC_BIT_EN                 # Halt ADC conversions, remain powered on
    mem32[adc+ADC_CS] =  0                                # Disable ADC
    print('ADC Value:'
          ,hex(cs)
          , cs / 4095 * 3.31
          , (cs & 0x0fff) / 4095 * 3.32
          )
    return cs

#
# Check the DMA busy flag.  If busy, return False (DMA still running) else
# disable further ADC cycles and return True (complete)
#
def dma_done(adc)->Boolean:
    if ((mem32[dma0+DMA_CH_CTRL] & (1<<DMA_BIT_BUSY))) > 0:
        return(False)
    else:
        mem32[adc+ADC_CS] = 0                   # disable ADC when done with sample collection    
        return(True)

#
# Wait for the ADC / DMA cycle to complete then
#  - disable the ADC
#  - return the elapsed time in uSec
#
def wait_for_dma(adc)->int:
    cnt = 0
    asn = time.ticks_us()
    while ((mem32[dma0+DMA_CH_CTRL] & (1<<DMA_BIT_BUSY))) > 0:   # Wait for DMA to complete
        cnt = cnt+1
        #time.sleep(.001)
    mem32[adc+ADC_CS] = 0                   # disable ADC when done with sample collection
    aen = time.ticks_us()
    return(int(aen-asn))

#
# Function to collect ADC sample using DMA.  The function returns immediately so the caller
# must poll for DMA complete before using the collected data
#
def adc_read_multi(adc,rate,samples) -> int:
    
    asn = time.ticks_us()
    mem32[adc+ADC_CS] =  1 << ADC_BIT_EN                  # Power ADC on
    
    # Clear FIFO
    while (mem32[adc+ADC_FCS] & (1 << FCS_BIT_FULL)) > 0:
        x = mem16[adc+ADC_FIFO]
        if DEBUG:
            print(".")
    
    
    if ADC_SHIFT:    # right shift result by four bits, 8 bit DMA transfer
        fcs = (1 << FCS_BIT_THRESH) | (1 << FCS_BIT_LEVEL) | (1 << FCS_BIT_OVER) | (1 << FCS_BIT_UNDER) | (1<<FCS_BIT_DREQEN) | (1 << FCS_BIT_SHIFT) | (1<<FCS_BIT_EN)
    else:            # 12 bit ADC result, 16 bit DMA transfer
        fcs = (1 << FCS_BIT_THRESH) | (1 << FCS_BIT_LEVEL) | (1 << FCS_BIT_OVER) | (1 << FCS_BIT_UNDER) | (1<<FCS_BIT_DREQEN) | (1<<FCS_BIT_EN)    
    mem32[adc+ADC_FCS] = fcs
    mem32[adc+ADC_DIV] = (48000000 // rate - 1) << ADC_DIV_INT  # Set ADC Sample rate
       
    mem32[dma0+DMA_CH_READ_ADDR] = ADC_BASE+ADC_FIFO                # DMA pulls data from ADC FIFO
    mem32[dma0+DMA_CH_WRITE_ADDR] = uctypes.addressof(adc_buffer)   # DMA writes to ada_buffer array
    mem32[dma0+DMA_CH_TRANS_COUNT] = samples                        # "samples" DMA tansfer.  Note that the ADC will continue
                                                                    # to run and fill fill the FIFO.  When the FIFO is full
                                                                    # the ADC willl set error indicators
    
    if ADC_SHIFT:    # byte wide DMA transfers
        dmactrl = (1<<DMA_BIT_INCR_WRITE) | (1<<DMA_BIT_IRQ_QUIET) | (DREQ_ADC<<DMA_BIT_TREQ_SEL) | (1<<DMA_BIT_EN)  # 8 bits
    else:
        dmactrl = (1<<DMA_BIT_INCR_WRITE) | (1<<DMA_BIT_IRQ_QUIET) | (1<<DMA_BIT_DATA_SIZE) | (DREQ_ADC<<DMA_BIT_TREQ_SEL) | (1<<DMA_BIT_EN)    
    mem32[dma0+DMA_CH_CTRL] = dmactrl
    
    cs = (1 << ADC_BIT_START_MANY) | 1 << ADC_BIT_EN             # Enable ADC in free run mode
    mem32[adc+ADC_CS] = cs                                       # start ADC

    aen = time.ticks_us()
    return(int(aen-asn))
    
#
# low pass filter the collected ADC samples.  The viper decorator uses integer
# arithmeic to [greatly] speed up operation > 10 times faster
#
@micropython.viper
def viper_lp_filter( buff:ptr16, length:int)->int:
    asn = time.ticks_us()
    cp = buff[0]
    cp1 = buff[1]
    for i in range(length-1):
        buff[i] = (cp >> 1) + (cp1 >> 1)
        cp = cp1
        cp1 = buff[i+1]
    aen = time.ticks_us()
    return(int(aen-asn))


#
# Return the minimimum and maximum values from the buffer
#
@micropython.viper
def viper_buffer_minmax(buff:ptr16,length:int):
    maxv = 0
    minv = 4095
    mininx = 0
    maxinx = 0
    for i in range(length-1):
        tmp = buff[i]
        if tmp > maxv:
            maxv = tmp
            maxinx = i
        if tmp < minv:
            minv = tmp
            mininx = i
    
    buff[mininx] = 2048
    buff[maxinx] = 2048
    
    for i in range(length-1):
        tmp = buff[i]
        if tmp > maxv:
            maxv = tmp
        if tmp < minv:
            minv = tmp
  
    return((int(minv),int(maxv)))

#
# This is the main program function called when the application starts
#
def main():

    print("Hello World")

    print("ADC_1 Return:",hex(adc_read_1_dbg(ADC_BASE)))

    v_ref = 3.3
    dev_scale = 1525 # Andy's scanner
#    dev_scale = 2225 # WA3NOA Bearcat BC125AT scanner
    
    while True:
      try:
        blink_led()
        minv = 0
        maxv = 0
        
        tm= adc_read_multi(ADC_BASE,ADC_RATE,ADC_SAMPLES)
        tm = wait_for_dma(ADC_BASE)
        #print(len(adc_buffer))
        #print(*adc_buffer[0:1000])
        tm = viper_lp_filter(adc_buffer,ADC_SAMPLES)
        print(*adc_buffer)
        #if (max(adc_buffer) > 3096):
        #    print("Bad buffer")
        time.sleep(0.5)
        #sys.exit()
#        for i in range(4):
#            tm= adc_read_multi(ADC_BASE,ADC_RATE,ADC_SAMPLES)
#            tm = wait_for_dma(ADC_BASE)
#            tm = viper_lp_filter(adc_buffer,ADC_SAMPLES)
#            #print(adc_buffer)  # filtered buffer
#            minmax = viper_buffer_minmax(adc_buffer,ADC_SAMPLES)
#            minv += minmax[0]
#            maxv += minmax[1]
#            
#        P2P = (maxv >> 2) - (minv >>2)
#    
#        devn = round(int(P2P*v_ref/4096*dev_scale+5),-1)
#        
#        print(minmax[0],",",minmax[1],",",P2P,",",devn,',')
#        #blink_led()
#        update_display(devn)

      except KeyboardInterrupt as e:
        print('caught <ctrl>-c .... exiting',e)
        sys.exit()


if __name__ == '__main__': 
    main()
