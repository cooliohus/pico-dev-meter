#
#    K3JSE Pico based deviation meter
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
#    The author can be contacted by email at k3jse@ccoolioh.com

import uctypes, time, array, sys, select
from machine import mem32,mem16, mem8, ADC, Pin, I2C
from os import uname
import _thread

DEBUG = False           # print debug and timing information

VERSION = "1.1.0 04/30/2026"

#OLED_TYPE = "SSD1306"
OLED_TYPE = "SH1106"

if OLED_TYPE == "SSD1306":
    from ssd1306 import SSD1306_I2C
elif OLED_TYPE == "SH1106":
    from sh1106 import SH1106_I2C

cpu_type = uname().machine.split(' ')[-1]

C_SHIFT = 3
C_CYCLES = 2**C_SHIFT
C_SCALE = 1.0

print("C_CYCLES:",C_CYCLES)

result_buffer = array.array('i', (0 for _ in range(3+C_CYCLES)))
result_buffer[0] = len(result_buffer)


#from rp2350regs import *
if cpu_type == 'RP2350':
    if DEBUG:
        print("CPU: rp2350")
    from rp2350regs import *
    from avg import avg
    l_avg = lambda buff,v : avg(buff,v)
elif cpu_type == 'RP2040':
    from rp2040regs import *
    from avg_pico import avg
    l_avg = lambda buff,v : avg(buff,v,C_SHIFT)

######################################################
#
# Some global stuff
#
#######################################################


HALT = 0
DUMP = 1
METER = 2
AVERAGE = 3
thread_done = True
is_connected = False
update_ready = False

mode = METER

#result_buffer = array.array('i', (0 for _ in range(3+8)))
#result_buffer[0] = len(result_buffer)

# Register sys.stdin (standard input) for monitoring read events with priority 1
poll_obj = select.poll()
poll_obj.register(sys.stdin, select.POLLIN)

# buffer to assemble incoming keys from the USB port
serial_buff = ""

if cpu_type == 'RP2350':
    regs = [200_000, 5000, C_SHIFT, 2047, 0.00001797804, 1.603437, -83.752, C_SCALE, 5000/1550, VERSION]    # HP
else:
    regs = [200_000, 5000, C_SHIFT, 2047, 0.00001200482, 1.630135, -102.449, C_SCALE, 5000/1550, VERSION]  # HP

mv = ['r',0,0,0,0,0,2047,0]   # meter values


ADC_MAX_SAMPLES = 6000
ADC_SHIFT   = False     # Select 8 bit or 12 bit ADC DMA transfers. True = 8 bit
ADC_PIN     = 26        # ADC channel 0
ADC_RATE    = regs[0]    # ADC sample rate
ADC_SAMPLES = regs[1]    # Number of samples for DMA count

have_oled = False

if ADC_SHIFT:           # Set maximum ADC count based on DMA shift
    ADC_MAX = 255
else:
    ADC_MAX = 4095

dma0 = DMA_BASE + 0        # Select DMA0

# Declare ADC buffer global to avoide allocation overhead
#if ADC_SHIFT:     # byte size buffer
#    adc_buffer = array.array('B', (0 for _ in range(ADC_SAMPLES)))   # DMA buffer for ADC, 'B' = bytes
#else:             # ushort (two byte) buffer
#    adc_buffer = array.array('H', (0 for _ in range(ADC_SAMPLES)))  # DMA buffer for ADC, 'H' = ushort, two bytes

adc_buffer = array.array('H', (0 for _ in range(ADC_MAX_SAMPLES)))  # DMA buffer for ADC, 'H' = ushort, two bytes
                                                                    # Reserve space for maximum 6000 samples

adc_init = ADC(Pin(ADC_PIN))                    # initialize ADC Pin

mem32[ADC_BASE+ADC_CS] = 1                      # Power on ADC


led = Pin("LED", Pin.OUT)
#pwm = Pin("GPIO23",Pin.OUT)
#pwm.value(True)


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

    i2c_dev = I2C(0,scl=Pin(21),sda=Pin(20),freq=400000)  # start I2C on I2C0 (GPIO 20/21)
    i2c_addr = [hex(ii) for ii in i2c_dev.scan()]         # get I2C address in hex format
    if i2c_addr==[]:
        print('No I2C Display Found') 
        return(False,False)
    else:
        print("I2C Address      : {}".format(i2c_addr[0])) # I2C device address
        print("I2C Configuration: {}".format(i2c_dev))     # print I2C params
        if OLED_TYPE == "SSD1306":
            oled = SSD1306_I2C(pix_res_x, pix_res_y, i2c_dev)  # oled controller
        elif OLED_TYPE == "SH1106":
            oled = SH1106_I2C(pix_res_x, pix_res_y, i2c_dev)   # oled controller
        else:
            return(False,False)
        oled.contrast(255)
        #oled.flip()
        return(oled,True)


def update_display(ooled,dev,ferror, err):
    if have_oled:
        if DEBUG:
            print("Updating Dislay",dev,ferror)
        if err == 0:
            s1 = '{:>4}'.format(dev) + " Hz."
        elif err == 1:
            s1 = "Overflow"
        elif err == 2:
            s1 = "Undeflow"
        else:
            s1 = "Unknown"

        ooled.fill(0) # clear screen
        ooled.fill_rect(0, 0, 127, 63, 1) # build big border
        ooled.fill_rect(2, 2, 124, 60, 0)
        ooled.text("Deviation:",25,10)
        ooled.text(" "+ s1 ,20,25)
        if abs(ferror) < 6:
            ferror = 0
        s1 = '{:>4}'.format(ferror)
        ooled.text("Ferr: "+s1+" Hz",5,45)
        ooled.show() # show new text

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
        mem32[adc+ADC_CS] = 0   # disable ADC when done with sample collection    
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
    
    fcs = (1 << FCS_BIT_THRESH) | (1 << FCS_BIT_LEVEL) | (1 << FCS_BIT_OVER) | (1 << FCS_BIT_UNDER) | (1<<FCS_BIT_DREQEN) | (1<<FCS_BIT_EN)    
    mem32[adc+ADC_FCS] = fcs
    mem32[adc+ADC_DIV] = (48000000 // rate - 1) << ADC_DIV_INT  # Set ADC Sample rate
       
    mem32[dma0+DMA_CH_READ_ADDR] = ADC_BASE+ADC_FIFO                # DMA pulls data from ADC FIFO
    mem32[dma0+DMA_CH_WRITE_ADDR] = uctypes.addressof(adc_buffer)   # DMA writes to adc_buffer array
    mem32[dma0+DMA_CH_TRANS_COUNT] = samples                        # "samples" DMA tansfer.  Note that the ADC will continue
                                                                    # to run and fill fill the FIFO.  When the FIFO is full
                                                                    # the ADC willl set error indicators
    
    dmactrl = (1<<DMA_BIT_INCR_WRITE) | (1<<DMA_BIT_IRQ_QUIET) | (1<<DMA_BIT_DATA_SIZE) | (DREQ_ADC<<DMA_BIT_TREQ_SEL) | (1<<DMA_BIT_EN)    
    mem32[dma0+DMA_CH_CTRL] = dmactrl
    
    cs = (1 << ADC_BIT_START_MANY) | 1 << ADC_BIT_EN             # Enable ADC in free run mode
    mem32[adc+ADC_CS] = cs                                       # start ADC

    aen = time.ticks_us()
    return(int(aen-asn))

#def lp_filter(buff,length)->int:
#    data = array.array('i', (0 for _ in range(7))) # Average over n-3 samples
#    data[0] = len(data)
#    asn = time.ticks_us()
#    for i in range(length):
#        l_avg(data,buff[i])
#    #    if cpu_type == 'RP2350':
#    #        buff[i] = avg(data,buff[i])
#    #    else:
#    #        buff[i] = avg(data,buff[i],2)
#    aen = time.ticks_us()
#    return(int(aen-asn))

#def result_filter(newval) -> int:
#    global result_buffer
#    if cpu_type == 'RP2350':
#        return(avg(result_buffer, newval))
#    else:
#        return(avg(result_buffer,newval,1))

def vm(s):
    global mode

    def cmd_avg(p):
        global mode
        mode = AVERAGE
        
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
        global regs, mv
        regs[3] =  mv[5]   # assumes meter is running
        #print("stm",regs[3])

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

    def cmd_ver(p):
        global regs
        print(regs[9])

    opcodes = {
        ">avg":cmd_avg,     # run in average mode
        ">bye":cmd_bye,     # disconnect from client
        ">con":cmd_con,     # connect to client
        ">dmp":cmd_dmp,     # dump one ASDC buffer to serial port then halt
        ">flp":cmd_flp,     # flip display (only some OLEDs)
        ">hlt":cmd_hlt,     # halt
        ">lsr":cmd_lsr,     # list registers
        ">rcf":load_regs,   # load registers from config file
        ">run":cmd_run,     # run in sliding window mode
        ">stm":cmd_stm,     # stoe median value to registers
        ">wcf":save_regs,   # save current registers to config file
        ">str":cmd_str,     # store value register
        ">ver":cmd_ver      # print vsersion
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
    #for i in range(1):
    tm = adc_read_multi(ADC_BASE,ADC_RATE,ADC_SAMPLES)
    tm = wait_for_dma(ADC_BASE)
    #tm = lp_filter(adc_buffer,ADC_SAMPLES)
    minv = min(adc_buffer[20:ADC_SAMPLES])
    maxv = max(adc_buffer[20:ADC_SAMPLES])

    P2P =  maxv - minv

    #deviation = int((P2P * regs[4]) + regs[5]) 
    deviation = int((P2P * P2P) * regs[4] + P2P*regs[5] + regs[6] )
    adc_buffer[0] = ADC_SAMPLES
    adc_buffer[1] = deviation
    #print(*adc_buffer[ADC_SAMPLES-10])
    print(*adc_buffer)
    mode = HALT
    thread_done = True


def run_meter(cycles=C_CYCLES):
    global regs,thread_done, mv, mode, update_ready, result_buffer
    
    f_P2P = 0
    while mode == METER:
        median = 0
        minv = 0
        maxv = 0
        err = 0
        asn = time.ticks_us()    
        for i in range(cycles):
            tm= adc_read_multi(ADC_BASE,ADC_RATE,ADC_SAMPLES)
            tm = wait_for_dma(ADC_BASE)
            #tm = lp_filter(adc_buffer,ADC_SAMPLES)
            #median += int(sum(adc_buffer) / len(adc_buffer))
            median += int(  sum(adc_buffer[20:ADC_SAMPLES]) / (ADC_SAMPLES-20) )
            #minv += min(adc_buffer[20:ADC_SAMPLES])
            #maxv += max(adc_buffer[20:ADC_SAMPLES])
            minv = min(adc_buffer[20:ADC_SAMPLES-20])
            maxv = max(adc_buffer[20:ADC_SAMPLES-20])
            #print(minv,maxv)
            if minv < 20:
                err = 2
            elif maxv > 4065:
                err = 1       
            #else:
            #    err = 0
            P2P = (maxv - minv) #>> 1
            #f_P2P= avg(result_buffer,P2P,3)
            f_P2P= l_avg(result_buffer,P2P)
            #print(P2P,f_P2P)
        
        #P2P = int((maxv - minv) >> 4)
        median = median >> C_SHIFT
        #deviation = int((f_P2P) * regs[4] + regs[5])
        #deviation = int(P2P * regs[4] + regs[5]) 
        #f_P2P = int(f_P2P)
        
        deviation = int(((f_P2P * f_P2P) * regs[4] + f_P2P*regs[5] + regs[6] ) * regs[7])
        #if cpu_type == 'RP2350':
        #    deviation = int((f_P2P * f_P2P) * regs[4] + f_P2P*regs[5] + regs[6] )
        #else:
        #    deviation = int((f_P2P) * regs[4] + regs[5])
        ferror = int((median - regs[3]) * regs[8])  #5000/1550)
        ase = time.ticks_us()
        #mv = [(ase-asn)/1000000,deviation,f_P2P,regs[3],median,ferror,'r',err]
        mv = ['r',err,deviation,ferror,f_P2P,median,regs[3],(ase-asn)/1000000]
        #print(mv[0],P2P,f_P2P,deviation)
        update_ready = True

    thread_done = True


def run_meter_avg(cycles=C_CYCLES):
    global regs,thread_done, mv, mode, update_ready
    
    while mode == AVERAGE:
        median = 0
        minv = 0
        maxv = 0
        err = 0
        asn = time.ticks_us()    
        for i in range(C_CYCLES):
            tm= adc_read_multi(ADC_BASE,ADC_RATE,ADC_SAMPLES)
            tm = wait_for_dma(ADC_BASE)
            #tm = lp_filter(adc_buffer,ADC_SAMPLES)
            median += int(  sum(adc_buffer[20:ADC_SAMPLES]) / (ADC_SAMPLES-20) )
            minv += min(adc_buffer[20:ADC_SAMPLES])
            maxv += max(adc_buffer[20:ADC_SAMPLES])
        
        maxv = maxv >> C_SHIFT
        minv = minv >> C_SHIFT
        if (maxv > 4065):
            err = 1
        elif  (minv < 20):
            err = 2
        P2P = maxv - minv
        median = median >> C_SHIFT
        #deviation = int(P2P * regs[4] + regs[5]) 
        #deviation = int((P2P * P2P) * regs[4] + P2P*regs[5] + regs[6] )
        deviation = int(((P2P * P2P) * regs[4] + P2P*regs[5] + regs[6] ) * regs[7])
        ferror = int((median - regs[3]) * 5000/1555)
        ase = time.ticks_us()
        #mv = [(ase-asn)/1000000,deviation,P2P,regs[3],median,ferror,'a',err]
        mv = ['a',err,deviation,ferror,P2P,median,regs[3],(ase-asn)/1000000]
        #mv = [(ase-asn)/1000000,deviation,P2P,regs[0],median,ferror,' ']
        update_ready = True

    thread_done = True

def get_chr():
    global serial_buff, poll_obj
    if ps := poll_obj.poll(5):    # wait 5 milliseconds
        try:
            #print("got chr")
            for (o, e) in ps:
                if o == sys.stdin and e == select.POLLIN:
                    #st = sys.stdin.readline().strip().lower().split(",")
                    ch = sys.stdin.read(1)
                    serial_buff += ch
                if ch == '\n':
                    #cmd1 = str(cmd_text.strip().lower().split(','))
                    cmd1 = str(serial_buff.strip().lower())
                    serial_buff = ''
                    vm(cmd1)
        except:
            pass


def main():
    global oled, have_oled, thread_done, is_connected, mode, update_ready, poll_obj
    
    #print("ADC_1 Return:",hex(adc_read_1_dbg(ADC_BASE) 
    (oled, have_oled) = init_oled(128,64)
    #update_display(oled,100,200)
    is_connected = False
    try:
        load_regs(1)
    except:
        print("No config file, using program defaults")

    while True:
        try:
            get_chr()

            if thread_done:
                if mode == AVERAGE:
                    thread_done = False
                    second_thread = _thread.start_new_thread(run_meter_avg, ())
                elif mode == METER:
                    thread_done = False
                    second_thread = _thread.start_new_thread(run_meter, ())
                elif mode == DUMP:
                    thread_done = False
                    second_thread = _thread.start_new_thread(dump_buffer, ())

            if update_ready:
                update_display(oled,mv[2],mv[3],mv[1])
                blink_led()
                update_ready = False
                if is_connected:
                    #adcval = mv[2].to_bytes(2, 'big')
                    #adcval = mv[3]
                    #fadcval = avg(result_buffer,mv[2],0)
                    print("<",mv[0],mv[1],mv[2],mv[3],mv[4],mv[5],mv[6],mv[7],">")           

        except KeyboardInterrupt as e:
            print('caught <ctrl>-c .... exiting',e)
            sys.exit()
    
    # never reach here

if __name__ == '__main__': 
    main()
