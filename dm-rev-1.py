import uctypes, time, array, sys, select
from machine import mem32,mem16, mem8, ADC, Pin, I2C

from os import uname

#from ssd1306 import SSD1306_I2C
from sh1106 import SH1106_I2C
from avg import avg
import _thread


DEBUG = False           # print debug and timing information

cpu_type = uname().machine.split(' ')[-1]

from rp2350regs import *
#if cpu_type == 'RP2350':
#    if DEBUG:
#        print("CPU: rp2350")
#    from rp2350regs import *
#    from avg import avg
#elif cpu_type == 'RP2040':
#    from rp2040regs import *
#    from avg_pico import avg


######################################################
#
# Some global stuff
#
#######################################################





print_buffer = False
deviation_run = True
cycle_complete = False

regs = [75_000, 5_000, 1, 3, 1.45370823508448, -105.391066423455, 2047, 7, 8, 9]
mv = []   # meter values


have_oled = False

ADC_SHIFT   = False     # Select 8 bit or 12 bit ADC DMA transfers. True = 8 bit
ADC_PIN     = 26
ADC_RATE    = regs[0]    # ADC sample rate
ADC_SAMPLES = regs[1]    # Number of samples for DMA count

if ADC_SHIFT:           # Set maximum ADC count based on DMA shift
    ADC_MAX = 255
else:
    ADC_MAX = 4095

dma0 = DMA_BASE         # Select DMA0

# Declare ADC buffer global to avoide allocation overhead
if ADC_SHIFT:     # byte size buffer
    adc_buffer = array.array('B', (0 for _ in range(ADC_SAMPLES)))   # DMA buffer for ADC, 'B' = bytes
else:             # ushort (two byte) buffer
    adc_buffer = array.array('H', (0 for _ in range(ADC_SAMPLES)))  # DMA buffer for ADC, 'H' = ushort, two bytes


adc_init = ADC(Pin(ADC_PIN))                    # initialize ADC Pin

mem32[ADC_BASE+ADC_CS] = 1                      # Power on ADC


led = Pin("LED", Pin.OUT)


#######################################################
#
# End of global stuff
#
#######################################################

###############################################################################
# Initialize the SSD1306 OLED display if present.
#
# The variable have_oled is set to false if there is no display present and the
# display routines will not attempt to update (a non-existant display)
#
def init_oled(x,y) -> tuple:
    global i2c_dev
    pix_res_x = x  # oled display horizontal resolution
    pix_res_y = y   # oled display vertical resolution

    i2c_dev = I2C(0,scl=Pin(21),sda=Pin(20),freq=400000)  # start I2C on I2C1 (GPIO 26/27)
    i2c_addr = [hex(ii) for ii in i2c_dev.scan()]         # get I2C address in hex format
    if i2c_addr==[]:
        print('No I2C Display Found') 
        return(False,False)
    else:
        print("I2C Address      : {}".format(i2c_addr[0])) # I2C device address
        print("I2C Configuration: {}".format(i2c_dev))     # print I2C params
        #oled = SSD1306_I2C(pix_res_x, pix_res_y, i2c_dev)  # oled controller
        oled = SH1106_I2C(pix_res_x, pix_res_y, i2c_dev)   # oled controller
        oled.flip()
        return(oled,True)


def update_display(oled,dev,ferror): #audio,dev, freq):
    if have_oled:
        if DEBUG:
            print("Updating Dislay",dev,ferror)
        s1 = '{:>4}'.format(dev)
        oled.contrast(255)
        oled.fill(0) # clear screen
        oled.fill_rect(0, 0, 127, 63, 1) # build big border
        oled.fill_rect(2, 2, 124, 60, 0)
        oled.text("Deviation:",25,10)
        oled.text(" "+ s1 + " Hz.",20,25)
        #s1 = '{:>4}'.format(ferror)
        if abs(ferror) < 6:
            ferror = 0
        oled.text("Ferr: "+str(ferror)+" Hz",5,45)
        oled.show() # show new text

def blink_led():
    led.value(not led.value())


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
def dma_done(adc)-> Boolean:
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
    elif cmd == 'm':
        regs[6] =  int(sum(adc_buffer) / len(adc_buffer))
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
    tm = lp_filter(adc_buffer,ADC_SAMPLES)
    #tm = viper_lp_filter(adc_buffer,ADC_SAMPLES)
    #vp2p = viper_find_p2p(adc_buffer,500,4500)
    #pmax += vp2p[0]
    #pavg += vp2p[1] / vp2p[2]
    print(*adc_buffer)
    print_buffer = False


def meter_run(cycles=4):
    global regs,cycle_complete, mv
    median = 0
    minv = 0
    maxv = 0

    asn = time.ticks_us()
    for i in range(cycles):
        #print("loop")
        tm= adc_read_multi(ADC_BASE,ADC_RATE,ADC_SAMPLES)
        tm = wait_for_dma(ADC_BASE)
                        
        tm = lp_filter(adc_buffer,ADC_SAMPLES-2000)
        median += sum(adc_buffer) / len(adc_buffer)
        minv += min(adc_buffer[100:ADC_SAMPLES-2000])
        maxv += max(adc_buffer[100:ADC_SAMPLES-2000])

    P2P = (maxv - minv) >> 2
    median = int(median) >> 2
    deviation = int((P2P) * regs[4] + regs[5]) 
        
    ase = time.ticks_us()    
            
    ferror = int((median - regs[6]) *5000/1755)
    #print((ase-asn)/1000000,',',deviation,',',P2P,',', regs[6], ',', median,',',ferror,',')
    mv = [(ase-asn)/1000000,deviation,P2P,regs[6],median,ferror,' ']

    update_display(oled,deviation,ferror)
    cycle_complete = True



def core1_thread():
    meter_run()

def main():
    global oled, have_oled, cycle_complete
     
     # Create a polling object instance
    poll_obj = select.poll()

    # Register sys.stdin (standard input) for monitoring read events with priority 1
    poll_obj.register(sys.stdin, select.POLLIN)

    (oled, have_oled) = init_oled(128,64)
    update_display(oled,100,200)
    
    while True:
        try:
 
            #print("ADC_1 Return:",hex(adc_read_1_dbg(ADC_BASE)))
            #time.sleep(2)

            second_thread = _thread.start_new_thread(meter_run, ())
            #print("running")
            while not cycle_complete:
                pass
            cycle_complete = False
            #print(eter_vals)
            print("<",mv[0],mv[1],mv[2],mv[3],mv[4],mv[5],">")

        except KeyboardInterrupt as e:
            print('caught <ctrl>-c .... exiting',e)
            sys.exit()
    
    # never reach here

if __name__ == '__main__': 
    main()
