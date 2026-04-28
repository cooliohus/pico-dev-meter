from __future__ import division
import serial, sys
import numpy as np
import scipy
from array import array
import matplotlib.pyplot as plt

FS = 75_000
FN = 15_000
FH = 6_000
FL = 300
FT = 200


#FS = 75_000
#FN = 15_000
#FH = 6_000
#FL = 750
#FT = 750

fL = FL / (FS / 2)
fH = FH / (FS / 2)
b = FT / (FS / 2)

#fL = 0.1  # Cutoff frequency as a fraction of the sampling rate (in (0, 0.5)).
#fH = 0.4  # Cutoff frequency as a fraction of the sampling rate (in (0, 0.5)).
#b = 0.008  # Transition band, as a fraction of the sampling rate (in (0, 0.5)).
N = int(np.ceil((4 / b)))
if not N % 2: N += 1  # Make sure that N is odd.
n = np.arange(N)
  
print(b, N)
 
# Compute a low-pass filter with cutoff frequency fH.
hlpf = np.sinc(2 * fH * (n - (N - 1) / 2))
hlpf *= np.blackman(N)
hlpf = hlpf / np.sum(hlpf)
 
  
 
# Compute a high-pass filter with cutoff frequency fL.
hhpf = np.sinc(2 * fL * (n - (N - 1) / 2))
hhpf *= np.blackman(N)
hhpf = hhpf / np.sum(hhpf)
hhpf = -hhpf
hhpf[(N - 1) // 2] += 1
 
#print(*hlpf)
#sys.exit()

# Convolve both filters.
h = np.convolve(hlpf, hhpf)
##h = array('f',(hlpf))
#h = array('f',(hhpf))

print(fH,fL,b,len(h))

#print(h[0:25])
#sys.exit()

#print(type(hlpf))
#h = array('f',(hlpf))
#print(len(hlpfa),type(hlpfa))
#print(hlpfa)
#del hlpf
#print(len(hlpf),type(hlpf))

#sys.exit()


ser = serial.Serial("/dev/ttyACM2",115200)
print(ser.name)
buff = []
buff = ser.readline()

while True:
    buffsum = 0
    bufffsum = 0
    for _ in range(5):
        ser_in = ser.readline().split()
        buff = [int(ser_in[x])-2065 for x in range(len(ser_in))]
        bufff = np.convolve(buff, h)
        buffsum  += max(buff[200:4500]) - min(buff[200:4500])
        bufffsum += max(bufff[1000:4000]) - min(bufff[1000:4000])
        #buffsum += max(bufff[250:len(bufff)]) - min(buff[250:len(bufff)])
    avgp2p = buffsum / 5
    favgp2p = bufffsum / 5
    print('p2p:',int(avgp2p), int(favgp2p))
    
    doplot = False
    
    if doplot:
        plt.figure()
        plt.subplot(211)
        plt.plot(buff)
        plt.title("Captured Waveform - 700Hz")
        plt.grid()
        #plt.show()
    
        plt.subplot(212)

        plt.plot(bufff)
        plt.title("Filtered Output")
        plt.grid(True)
    
        plt.tight_layout()
        plt.show()

    
    #sys.exit()

print(type(buff))
print(len(buff),buff)
buffx = [byte for byte in buff]
print(type(buffx))
#buffx = list(buff)
#print(type(buffx))
print(len(buff),buffx)
plt.plot(buffx)
#plt.grid()
plt.show()


ser.close()