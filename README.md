
# pico-dev-meter

## Commands

### >avg

Start the meter in AVERAGE mode using DMA buffer averaging.  See also >run

### >bye

Sent by an appliction to disconnect from the meter.  The meter will stop sending status information to the serial port

### >con
Sent by an application to connect to the meter.  The meter will start sending status information to the serial port

### >css
Change the mode to CTCSS filter to remove a PL Tone if present.  Use >run to return to non-filtered mode.  I plan to 
make this a togggle option later.

### >dmp

The meter will collect one DMA buffer and send to the serial port.  buffer[0] contains the buffer length and buffer[1] contains the calculated deviation value.  The meter will enter HALT mode after completing.  Seee the avg and run commands to restart operation

### >flp

Flip the OLED display 180 degrees.  This only works on compatible OLED displays such as the SH1106

### >hlt

Place the meter into HALT mode. ADC / DMA collection halts and display updates are paused

### >lsr

List the configuration and operational registers
```
    r[0] ADC sample rate
    r[1] DMA buffer size, maximum = 6000
    r[2] buffers to average 2^^r[2]
    r[3] ADC value for DC operating point, default = 2047
    r[4] x*x coefficient
    r[5]   x coefficient
    r[6]     constant
    r[7] Scale factor, default = 1.0 
    r[8] Frequency error multiplier
    r[9] Version
```
### >rcf
Load registers from the configuration file

### >run

Start the meter in RUN mode using DMA buffer sliding windows averaging (default).  See also >avg

### >stm

Store the average DC value of the current DMA buffer to register r[3].  This value is used to calculate frequency error
```
    error = (r[3] + <current DMA buffer avergage>) * r[8]
```
### scf

Save the current register values to the configuration file

## >ssr
Change sample rate and sample counr (Store Sample Rate)
```
    >ssr,<sample rate>,<sample count>
```

### >str
Store a new value to a configuration register
```
    >str,<register number>,<value>
```

### >ver

Print the version number to the serial port

## Serial port output format

Data items writen to the serial port
```
mode: a=average, r=run
error: 0 = no error
deviation (Hz)
frequency error (Hz)
DMA buffer P2P value, ADC count
DC value of current DMA buffer, ADC count
ADC reference value for frequency error calculation
Cycle time (seconds)
```