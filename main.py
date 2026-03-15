# Pico 2

import uctypes, time, array, sys, select
from machine import mem32,mem16, mem8, ADC, Pin, I2C

from os import uname

#import framebuf
from ssd1306 import SSD1306_I2C
import onewire
#import rp2, select
#import serial
#ser = serial.Serial("/dev/ttyACM1")
#print(ser.name)

from rp2350regs import *

cpu_type = uname().machine.split(' ')[-1]
if cpu_type == 'RP2350':
    from rp2350regs import *
    from avg import avg
elif cpu_type == 'RP2040':
    from rp2040regs import *
    from avg_pico import avg

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

DEBUG = False           # print debug and timing information
print_buffer = False
deviation_run = True



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
#led_pin = 25  # Pico
#led = Pin(led_pin,Pin.OUT)
#ledmask = 1<<led_pin

led = Pin("LED", Pin.OUT)


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

    led.value(not led.value())

    # create a python integer from a four byte memory slice at offset (pin# * 8) as each pin has a
    # four byte status register and four byte control register.  "+4" steps over the status register
    #if DEBUG:
    #    d32 = mem32[GPIO_BASE+led_pin*8+4]
    #    print('GPIO',led_pin,'ctrl register (pg 243,247:',hex(d32),bin(d32))
    #    d32 = mem32[PAD_BASE+led_pin*8+4] 
    #    print('GPIO',led_pin,'pad register (pg 299,300):',hex(d32),bin(d32))
    
        # Display gpio output enable register - bit 13 or 25 should be set
        # "sio" is what RP2040 calls digital io
    #    oe = mem32[SIO_BASE+led_pin*8+4] 
    #    print('GPIO Output Enable (pg 42 and on), :',hex(oe),bin(oe))

    #for _ in range(5):
    #    mem32[SIO_BASE+GPIO_OUT_SET] = ledmask
    #    time.sleep(1)
    #    mem32[SIO_BASE+GPIO_OUT_CLR] = ledmask
    #    time.sleep(1)
    #mem32[SIO_BASE+GPIO_OUT_XOR] = ledmask

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

def lp_filter(buff,length)->int:
    data = array.array('i', (0 for _ in range(5))) # Average over 16 samples
    data[0] = len(data)
    asn = time.ticks_us()
    for i in range(length):
        if cpu_type == 'RP2350':
            buff[i] = avg(data,buff[i])
        else:
            buff[i] = avg(data,buff[i],2)
    aen = time.ticks_us()
    return(int(aen-asn))
#
# Return the minimimum and maximum values from the buffer
#
@micropython.viper
def viper_buffer_minmax(buff:ptr16,buff_len:int):
    buff_ofs = 100
    buff_len = 4900
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
        val = buff[indx]
        if val >= p2p_peak:
            p2p_peak = val
            p2p_indx = indx
            indx += 1
        elif (p2p_peak - val) < 100:
            indx += 1
        else:
            indx += 1
            break
      #print("peak:",p2p_indx,p2p_peak)

      # Look for a trough
      p2p_trough = 4096     
      while indx < bend:
          val = buff[indx]
          if val <= p2p_trough:
            p2p_trough = val
            p2p_indx = indx
            indx += 1
          elif (val - p2p_trough) < 100:
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

#1.4784946236559 -129.704301075269
regs = [75_000, 5_000, 1, 3, 1.47770016120365, 129.231595916174, 6, 7, 8, 9]

#    R0: sample rate
#    R1: sample count
#    R3  Capturte cycles

def vmx(st):
    global print_buffer, deviation_run
    # "virtual machine" implementing core functionality
    #print("entering vm",st)
    #print("st: ",st)
    cmdstr = st.split(",")
    #print("DEBUG:",cmdstr)
    #print(cmdstr[0])
    cmd = cmdstr[0]
    if (cmd[0] != '>'):
        print("cmd error, ignoring",cmdstr)
        cmd = ""
    else:
        cmd = cmd[1]
        #print("cmd:",cmd)
    if cmd == "":
        pass
    elif cmd == 'd':
        deviation_run = False
        print_buffer = True
    elif cmd == 'x':
        deviation_run = True
    elif cmd == 'h':
        deviation_run = False
        print_buffer =False
    elif cmd == "r":
       # Set new register value
                    #   st[1] is register to update
                    #   st[2] is new register value
        if len(cmdstr) < 3:
            print("Not enough parameters for register comand")
        else:
            try:
                #print("opcode:", cmdstr[0], int(cmdstr[1]), int(cmdstr[2]))
                # if (int(st[1])!=0) and ((int(st[2]) < 500) or (int(st[2]) > 5000)):
                #    print("Parameter out of range")
                #    break
                #print("Writing Registers")
                try:
                    n = int(cmdstr[2])
                except:
                    try:
                        n = float(cmdstr[2])
                    except:
                        n = cmdstr[2]
                regs[int(cmdstr[1])] = n
            except:
                print(">str: Parameter Error")
    elif cmd == "l":
        # list the values contained in all 10 virtual registers
        #:print("list registers")
        print(regs)

def dump_buffer():
    global print_buffer
    tm= adc_read_multi(ADC_BASE,ADC_RATE,ADC_SAMPLES)
    tm = wait_for_dma(ADC_BASE)
    #tm = lp_filter(adc_buffer,ADC_SAMPLES)
    tm = viper_lp_filter(adc_buffer,ADC_SAMPLES)
    #vp2p = viper_find_p2p(adc_buffer,500,4500)
    #pmax += vp2p[0]
    #pavg += vp2p[1] / vp2p[2]
    print(*adc_buffer)
    print_buffer = False
    #time.sleep(2)

def main():
    global print_buffer
    #print("Hello World")
    #print("ADC_1 Return:",hex(adc_read_1_dbg(ADC_BASE)))

    # Create a polling object instance
    poll_obj = select.poll()

    # Register sys.stdin (standard input) for monitoring read events with priority 1
    poll_obj.register(sys.stdin, select.POLLIN)


#    v_ref = 3.3
#    dev_scale = 1525 # Andy's scanner
#    dev_scale = 2225 # WA3NOA Bearcat BC125AT scanner

    cmd_text = ''
    cmd1 = ''
    
    ##print_buffer = False

    while True:
      try:
        blink_led()
    
        if ps := poll_obj.poll(10):    # wait 10 milliseconds
            try:
                for (o, e) in ps:
                    if o == sys.stdin and e == select.POLLIN:
                        #st = sys.stdin.readline().strip().lower().split(",")
                        ch = sys.stdin.read(1)
                        cmd_text += ch
                        #print('cmd_text:',cmd_text)
                        #print(cmd_text)
                        if ch == '\n':
                            #cmd1 = str(cmd_text.strip().lower().split(','))
                            cmd1 = str(cmd_text.strip().lower())
                            #print("cmd:",cmd1)
                            cmd_text = ''
                            vmx(cmd1)
                            cmd1 = ''
            except:
                pass
        
        #if cmd1 != '':
        #    vmx(cmd1)
        #    cmd1 = ''
 
        if deviation_run:
            minv = 0
            maxv = 0
            pmax = 0
            pavg = 0
            #p2pminmax = 0
       
            asn = time.ticks_us()
            for i in range(4):
                #print("loop")
                tm= adc_read_multi(ADC_BASE,ADC_RATE,ADC_SAMPLES)
                tm = wait_for_dma(ADC_BASE)
                ##tm = viper_lp_filter(adc_buffer,ADC_SAMPLES)
                
                ##minv = min(adc_buffer[100:4900])
                ##maxv = max(adc_buffer[100:4900])
                ##print("before:",tm,minv,maxv,maxv-minv)
                #tm = viper_lp_filter(adc_buffer,ADC_SAMPLES-2000)
                
                tm = lp_filter(adc_buffer,ADC_SAMPLES-2000)
                #tm = viper_lp_filter(adc_buffer,ADC_SAMPLES-2000)
                #minmax = viper_buffer_minmax(adc_buffer[500:4500],ADC_SAMPLES-1000)
                #print(tm,minmax)
                #minv += minmax[0]
                #maxv += minmax[1]
                minv += min(adc_buffer[100:ADC_SAMPLES-2000])
                maxv += max(adc_buffer[100:ADC_SAMPLES-2000])
                ##print("after:",tm,minv,maxv,maxv-minv)
                ##vp2p = viper_find_p2p(adc_buffer,500,4500)
                ##pmax += vp2p[0]
                ##pavg += vp2p[1] / vp2p[2]
            P2P = (maxv - minv) >> 2
            ##VP2PMAX = pmax >> 3
            ##VP2PAVG = int(pavg) >> 3
            
            ##deviation = int((P2P- 359) * 2.53950338600452 + 750)
            #deviation = int((P2P) * 2.57994917026621 -190.543650755598)  # Non-inverting
            #deviation = int((P2P) * 1.4784946236559 -129.704301075269)  # inverting
            deviation = int((P2P) * regs[4] -regs[5])  # inverting
        
            ase = time.ticks_us()    
        
            print((ase-asn)/1000000,',',deviation,',',P2P,',', 0,',')
            ##print((ase-asn)/1000000,',',deviation,',', VP2PMAX,',', vp2p[2],',')
            update_display(deviation)
        elif print_buffer:
            dump_buffer()


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

