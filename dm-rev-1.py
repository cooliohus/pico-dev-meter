import uctypes, time, array, sys, select
from machine import mem32,mem16, mem8, ADC, Pin, I2C

from os import uname

#from ssd1306 import SSD1306_I2C
from sh1106 import SH1106_I2C


cpu_type = uname().machine.split(' ')[-1]
if cpu_type == 'RP2350':
    from rp2350regs import *
    from avg import avg
elif cpu_type == 'RP2040':
    from rp2040regs import *
    from avg_pico import avg


######################################################
#
# Some global stuff
#
#######################################################




DEBUG = False           # print debug and timing information
print_buffer = False
deviation_run = True

regs = [75_000, 5_000, 1, 3, 1.45370823508448, 105.391066423455, 2047, 7, 8, 9]
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
def init_oled(x,y) -> Object:
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

#pix_res_x = 128  # oled display horizontal resolution
#pix_res_y = 64   # oled display vertical resolution

#i2c_dev = I2C(0,scl=Pin(21),sda=Pin(20),freq=400000)  # start I2C on I2C1 (GPIO 26/27)
#i2c_addr = [hex(ii) for ii in i2c_dev.scan()]         # get I2C address in hex format
#if i2c_addr==[]:
#    print('No I2C Display Found') 
#else:
#    print("I2C Address      : {}".format(i2c_addr[0])) # I2C device address
#    print("I2C Configuration: {}".format(i2c_dev))     # print I2C params
#    have_oled = True
#    #oled = SSD1306_I2C(pix_res_x, pix_res_y, i2c_dev)  # oled controller
#    oled = SH1106_I2C(pix_res_x, pix_res_y, i2c_dev)   # oled controller
#    oled.flip()



def update_display(oled,dev,ferror): #audio,dev, freq):
    if have_oled:
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

(oled, have_oled) = init_oled(128,64)
update_display(oled,1,2)
while True:
    pass



















cpu_type = uname().machine.split(' ')[-1]
if cpu_type == 'RP2350':
    from rp2350regs import *
    from avg import avg
elif cpu_type == 'RP2040':
    from rp2040regs import *
    from avg_pico import avg

