# Pico 1

import uctypes, time, array, sys, select
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

GPIO_BASE       = 0x40014000   # IO_BANK0_BASE Page 25
GPIO_CHAN_WIDTH = 0x08
GPIO_PIN_COUNT  = 30
PAD_BASE        = 0x4001c000
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
DMA_CHAN_COUNT  = 12

# DMA Channel Registers 0ne per channel relative to DMA_BASE (pg 91)
DMA_CH_READ_ADDR    = 0x00
DMA_CH_WRITE_ADDR   = 0x04
DMA_CH_TRANS_COUNT  = 0x08
DMA_CH_CTRL         = 0x0C

########## DMA CTRL Register Defines (pg 112) ##########
DMA_BIT_AHB_ERROR   = 31
DMA_BIT_READ_ERROR  = 30
DMA_BIT_WRITE_ERROR = 29
DMA_BIT_BUSY        = 24
DMA_BIT_SNIFF_EN    = 23
DMA_BIT_BSWP        = 22
DMA_BIT_IRQ_QUIET   = 21
DMA_BIT_TREQ_SEL    = 15
DMA_BIT_RING_SELECT = 10
DMA_BIT_RING_SIZE   = 6
DMA_BIT_INCR_WRITE  = 5
DMA_BIT_INCR_READ   = 4
DMA_BIT_DATA_SIZE   = 2
DMA_BIT_HIGH_PRIOR  = 1
DMA_BIT_EN          = 0

# See pg 95 for DREQ channels
DREQ_ADC = 36


# DREQ DREQ Channel   DREQ DREQ Channel   DREQ DREQ Channel    DREQ DREQ Channel
#    0 DREQ_PIO0_TX0    10 DREQ_PIO1_TX2    20 DREQ_UART0_TX     30 DREQ_PWM_WRAP6
#    1 DREQ_PIO0_TX1    11 DREQ_PIO1_TX3    21 DREQ_UART0_RX     31 DREQ_PWM_WRAP7
#    2 DREQ_PIO0_TX2    12 DREQ_PIO1_RX0    22 DREQ_UART1_TX     32 DREQ_I2C0_TX
#    3 DREQ_PIO0_TX3    13 DREQ_PIO1_RX1    23 DREQ_UART1_RX     33 DREQ_I2C0_RX
#    4 DREQ_PIO0_RX0    14 DREQ_PIO1_RX2    24 DREQ_PWM_WRAP0    34 DREQ_I2C1_TX
#    5 DREQ_PIO0_RX1    15 DREQ_PIO1_RX3    25 DREQ_PWM_WRAP1    35 DREQ_I2C1_RX
#    6 DREQ_PIO0_RX2    16 DREQ_SPI0_TX     26 DREQ_PWM_WRAP2    36 DREQ_ADC
#    7 DREQ_PIO0_RX3    17 DREQ_SPI0_RX     27 DREQ_PWM_WRAP3    37 DREQ_XIP_STREAM
#    8 DREQ_PIO1_TX0    18 DREQ_SPI1_TX     28 DREQ_PWM_WRAP4    38 DREQ_XIP_SSITX
#    9 DREQ_PIO1_TX1    19 DREQ_SPI1_RX     29 DREQ_PWM_WRAP5    39 DREQ_XIP_SSIRX



# Selected ADC-CH_CTRL defines (pg 112)
ADC_CTRL_BUSY       = 24
ADC_CTRL_TR_SEL     = 15		# See pg 95 for DREQ channels (above)
ADC_CTRL_INC_WRITE  = 5
ADC_CTRL_INC_READ   = 4
ADC_CTRL_DATA_SIZE  = 2
ADC_CTRL_EN         = 0

########## ADC Register Defines (pg 563) ##########
ADC_BASE            = 0x4004c000
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
GPIO_OUT_SET        = 0x14
GPIO_OUT_CLR        = 0x18
GPIO_OUT_XOR        = 0x1C
GPIO_OE             = 0x20
GPIO_OE_SET         = 0x24
GPIO_OE_CLR         = 0x28
GPIO_OE_XOR         = 0x2C


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
    #print('No I2C Display Found') 
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

DEBUG = False           # print debug and timing information

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


if DEBUG:
    print("End Globnal")
    
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
    cp = (buff[0])  #& 0xfff0
    cp1 = (buff[1])  # & 0xfff0
    for i in range(length-1):
        buff[i] = (cp >> 1) + (cp1 >> 1)
        cp = cp1
        cp1 = (buff[i+1]) # & 0xfff0
    aen = time.ticks_us()
    return(int(aen-asn))


#
# Return the minimimum and maximum values from the buffer
#
@micropython.viper
def viper_buffer_minmax(buff:ptr16,buff_len:int):
    buff_ofs = 1500
    buff_len = 2500
    maxv = 0
    minv = 4095
    mininx = 0
    maxinx = 0
    for i in range(buff_len-1):
        tmp = buff[buff_ofs+i]
        if tmp > maxv:
            maxv = tmp
            maxinx = i
        if tmp < minv:
            minv = tmp
            mininx = i
    
    buff[mininx] = 2048
    buff[maxinx] = 2048
    
    for i in range(buff_len-1):
        tmp = buff[buff_ofs+i]
        if tmp > maxv:
            maxv = tmp
        if tmp < minv:
            minv = tmp
  
    return((int(minv),int(maxv)))

@micropython.viper
def viper_find_p2p(buff:ptr16,bstart:int,bend:int)->object:
    #print("entering find p2p")
    p2p_sum = 0
    p2p_count = 0
    p2p_index = 0
    #p2p_last
    p2p_max = 0
    p2p_avg = 0
    p2p_peak = 0
    p2p_trough = 4096
    indx = bstart
    
    asn = time.ticks_us()
    
    
    while indx < bend:
      p2p_peak = 0  
      while indx < bend:
        # look for the next peak
        if buff[indx] >= p2p_peak:
            p2p_peak = buff[indx]
            p2p_indx = indx
            indx += 1
        elif (p2p_peak - buff[indx]) < 10:
            indx += 1
        else:
            indx += 1
            break
      #print("peak:",p2p_indx,p2p_peak)

      # Look for a trough
      p2p_trough = 4096     
      while indx < bend:
          if buff[indx] <= p2p_trough:
            p2p_trough = buff[indx]
            p2p_indx = indx
            indx += 1
          elif (buff[indx] - p2p_trough) < 10:
            indx += 1
          else:
            indx += 1
            break
      #print("trough:",indx,p2p_trough)
        
      
      # ignore last possibly incomplete cycle
      if indx < bend:
          p2p = p2p_peak - p2p_trough
          if p2p > p2p_max:
              p2p_max = p2p
          p2p_sum += p2p
          p2p_count += 1
        
    tm = time.ticks_us() - asn
    #print(tm, p2p_max,p2p_sum, p2p_count)
    return(p2p_max,p2p_sum, p2p_count, tm)

#
# This is the main program function called when the application starts
#

regs = [19_600_000, 1500, 2500, 3, 4, 5, 6, 7, 8, 9]

def vm(st):
    # "virtual machine" implementing core functionality
    #print("entering vm")
    #print("st: ",st)
    cmdstr = st.split(",")
    print(cmdstr)
    print(cmdstr[0])
    cmd = cmdstr[0]
    if (cmd[0] != '>'):
        print("cmd error, ignoring",cmdstr)
        cmd = ""
    else:
        cmd = cmd[1]
        print("cmd:",cmd)
    if cmd == "":
        pass
    elif cmd == "r":
       # Set new register value
                    #   st[1] is register to update
                    #   st[2] is new register value
        if len(cmdstr) < 3:
            print("Not enough parameters for register comand")
        else:
            try:
                print("opcode:", cmdstr[0], int(cmdstr[1]), int(cmdstr[2]))
                # if (int(st[1])!=0) and ((int(st[2]) < 500) or (int(st[2]) > 5000)):
                #    print("Parameter out of range")
                #    break
                print("Writing Registers")
                regs[int(cmdstr[1])] = int(cmdstr[2])
            except:
                print("Parameters not numeric")
    elif cmd == "l":
        # list the values contained in all 10 virtual registers
        print("list registers")
        print(regs)


def main():

    #print("Hello World")
    #print("ADC_1 Return:",hex(adc_read_1_dbg(ADC_BASE)))

    #usb_in = pyb.USB_VCP()
    # Create a polling object instance
    poll_obj = select.poll()

    # Register sys.stdin (standard input) for monitoring read events with priority 1
    poll_obj.register(sys.stdin, select.POLLIN)
    #poll_obj.register(usb_in, select.POLLIN)
    
    
    #data = usb.recv(10, timeout=500)
    #if len(data) < 10:
    #   print('timeout')


    v_ref = 3.3
    dev_scale = 1525 # Andy's scanner
#    dev_scale = 2225 # WA3NOA Bearcat BC125AT scanner
    
    while True:
      try:
        blink_led()
    
        if ps := poll_obj.poll(10):    # wait 10 milliseconds
            try:
                for (o, e) in ps:
                    if o == sys.stdin and e == select.POLLIN:
                        #st = sys.stdin.readline().strip().lower().split(",")
                        st = sys.stdin.readline().strip().lower()
                        #st = usb_in.readline(timeout=100).readline().strip().lower()
                        #print("serial cmd: ",st)
                        vm(st)
            except:
                pass
    
        minv = 0
        maxv = 0
        pmax = 0
        pavg = 0
        #p2pminmax = 0
        
        #tm= adc_read_multi(ADC_BASE,ADC_RATE,ADC_SAMPLES)
        #tm = wait_for_dma(ADC_BASE)
        #print(len(adc_buffer))
        #print(*adc_buffer[0:1000])
        #tm = viper_lp_filter(adc_buffer,ADC_SAMPLES)
        #print(*adc_buffer)
        #time.sleep(0.5)
        #sys.exit()
        asn = time.ticks_us()
        for i in range(8):
            #print("loop")
            tm= adc_read_multi(ADC_BASE,ADC_RATE,ADC_SAMPLES)
            tm = wait_for_dma(ADC_BASE)
            tm = viper_lp_filter(adc_buffer,ADC_SAMPLES)
            #print(*adc_buffer[1500:2000])  # filtered buffer
            minmax = viper_buffer_minmax(adc_buffer,ADC_SAMPLES)
            minv += minmax[0]
            maxv += minmax[1]
            vp2p = viper_find_p2p(adc_buffer,1500,2500)
            pmax += vp2p[0]
            #pavg += vp2p[1] / vp2p[2]
        P2P = (maxv - minv   ) >> 3
        VP2PMAX = pmax >> 3
        VP2PAVG = int(pavg) >> 3
        #P2P = maxv - minv

#        deviation = int((P2P-816) * 1.37741046831956 + 1000)
        deviation = int((VP2PMAX-875) * 1.26968004062976 + 1000)
        
        ase = time.ticks_us()    
        #P2P = (maxv >> 3) - (minv >>3)
        
        print((ase-asn)/1000000,',',deviation,',',P2P,',', VP2PMAX,',', vp2p[2],',')
        #print(*adc_buffer)
        #time.sleep(0.5)


        #print((ase-asn)/1000000,',',deviation,',',VP2PMAX)
        #sys.exit()
        #print((ase-asn)/1000000,P2P)
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
