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




HALT = 0
DUMP = 1
METER = 2
thread_done = True
is_connected = False
update_ready = False

mode = METER

result_buffer = array.array('i', (0 for _ in range(3+3)))
result_buffer[0] = len(result_buffer)

# Register sys.stdin (standard input) for monitoring read events with priority 1
poll_obj = select.poll()
poll_obj.register(sys.stdin, select.POLLIN)

# buffer to assemble incoming keys from the USB port
serial_buff = ""

# 750-4000
regs = [150_000, 3500, 1, 2047, 1.46982162160107, -116.49969366293, 6, 7, 8, 9]
#regs = [75_000, 2_500, 1, 2047, 1.47058823529412, -125, 6, 7, 8, 9]

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

def save_regs(p):
    import json
    with open('regs.json', 'w') as f:
        json.dump(regs, f)

def load_regs(p):
    import json
    with open('regs.json', 'r') as f:
        regs = json.load(f)

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
    data = array.array('i', (0 for _ in range(7))) # Average over n-3 samples
    data[0] = len(data)
    asn = time.ticks_us()
    for i in range(length):
    #    if cpu_type == 'RP2350':
        buff[i] = avg(data,buff[i])
    #    else:
    #        buff[i] = avg(data,buff[i],2)
    aen = time.ticks_us()
    return(int(aen-asn))

def result_filter(newval) -> int:
    global result_buffer
    if cpu_type == 'RP2350':
        return(avg(result_buffer, newval))
    else:
        return(avg(result_buffer,newval,2))

def vm(s):
    global mode

    def cmd_bye(p):
        global mode, is_connected
        is_connected = False

    def cmd_con(p):
        global mode, is_connected
        is_connected = True

    def cmd_dmp(p):
        global mode
        mode = DUMP

    def cmd_flp(p):
        global oled
        oled.flip()

    def cmd_hlt(p):
        global mode
        mode = HALT

    def cmd_lsr(p):
        global mode
        print(regs)

    def cmd_stm(p):
        global regs
        regs[3] =  int(sum(adc_buffer) / len(adc_buffer))

    def cmd_run(p):
        global mode
        mode = METER

    def cmd_str(p):
        global mode
        if len(cmdstr) < 3:
            print("Not enough parameters for register comand")
        else:
            try:
                n = int(cmdstr[2])
            except:
                try:
                    n = float(cmdstr[2])
                except:
                    n = cmdstr[2]
            regs[int(cmdstr[1])] = n


    opcodes = {
        ">bye":cmd_bye,
        ">con":cmd_con,
        ">dmp":cmd_dmp,
        ">flp":cmd_flp,
        ">hlt":cmd_hlt,
        ">lsr":cmd_lsr,
        ">rdr":load_regs,
        ">run":cmd_run,
        ">stm":cmd_stm,
        ">wrr":save_regs,
        ">str":cmd_str
    }
    cmdstr = s.split(",") 
    if cmdstr[0] in opcodes:
        #print("valid op")
        opcodes[cmdstr[0]](cmdstr)

def dump_buffer():
    global mode, thread_done, regs
    minv = 0
    maxv = 0
    #print("dump buffer")
    for i in range(4):
        tm= adc_read_multi(ADC_BASE,ADC_RATE,ADC_SAMPLES)
        tm = wait_for_dma(ADC_BASE)
        tm = lp_filter(adc_buffer,ADC_SAMPLES)
        minv += min(adc_buffer[20:ADC_SAMPLES])
        maxv += max(adc_buffer[20:ADC_SAMPLES])

    P2P =  (maxv - minv) >> 2

    deviation = int((P2P) * regs[4] + regs[5]) 
    adc_buffer[0] = deviation
    print(*adc_buffer)
    mode = HALT
    thread_done = True


def run_meter(cycles=2):
    global regs,thread_done, mv, mode, update_ready
    
    while mode == METER:
        median = 0
        minv = 0
        maxv = 0
        asn = time.ticks_us()    
        for i in range(cycles):
            #print("loop")
            tm= adc_read_multi(ADC_BASE,ADC_RATE,ADC_SAMPLES)
            tm = wait_for_dma(ADC_BASE)
            tm = lp_filter(adc_buffer,ADC_SAMPLES)
            median += sum(adc_buffer) / len(adc_buffer)
            minv += min(adc_buffer[20:ADC_SAMPLES])
            maxv += max(adc_buffer[20:ADC_SAMPLES])
        
        P2P = (maxv - minv) >> 1
        median = int(median) >> 1
        
        f_P2P= avg(result_buffer,P2P)
        #print(P2P,f_P2P)
        
        deviation = int((f_P2P) * regs[4] + regs[5]) 
        ferror = int((median - regs[3]) * 5000/1755)
        ase = time.ticks_us()
        mv = [(ase-asn)/1000000,deviation,f_P2P,regs[3],median,ferror,' ']
        update_ready = True

    thread_done = True


def get_chr():
    global serial_buff, poll_obj
    if ps := poll_obj.poll(500):    # wait 10 milliseconds
        try:
            #print("got chr")
            for (o, e) in ps:
                if o == sys.stdin and e == select.POLLIN:
                    #st = sys.stdin.readline().strip().lower().split(",")
                    ch = sys.stdin.read(1)
                    #print(ord(ch))
                    serial_buff += ch
                    #print('cmd_text:',cmd_text)
                    #print(cmd_text)
                if ch == '\n':
                    #cmd1 = str(cmd_text.strip().lower().split(','))
                    cmd1 = str(serial_buff.strip().lower())
                    #print("cmd:",cmd1)
                    serial_buff = ''
                    #vmx(cmd1)
                    vm(cmd1)
        except:
            pass


def main():
    global oled, have_oled, thread_done, is_connected, mode, update_ready, poll_obj
    
    #print("ADC_1 Return:",hex(adc_read_1_dbg(ADC_BASE) 
    (oled, have_oled) = init_oled(128,64)
    update_display(oled,100,200)
    is_connected = False

    while True:
        try:
            get_chr()

            if (mode == METER and thread_done):
                #print("meter")
                thread_done = False
                #second_thread = _thread.start_new_thread(run_meter, ())
                second_thread = _thread.start_new_thread(run_meter, ())
                #run_meter()
            elif (mode == DUMP and thread_done):
                #print("dump")
                thread_done = False
                #second_thread = _thread.start_new_thread(dump_buffer, ())
                second_thread = _thread.start_new_thread(dump_buffer, ())

            if update_ready:
                update_display(oled,mv[1],mv[5])
                update_ready = False
                if is_connected:
                    adcval = mv[2].to_bytes(2, 'big')
                    fadcval = avg(result_buffer,mv[2])
                    #print(mv[2],adcval,fadcval)
                    print("<",mv[0],mv[1],fadcval,mv[3],mv[4],mv[5],">")
            
            #while not meter_done:
            #    pass
            #cycle_complete = False
            #print(eter_vals)
            

        except KeyboardInterrupt as e:
            print('caught <ctrl>-c .... exiting',e)
            sys.exit()
    
    # never reach here

if __name__ == '__main__': 
    main()
