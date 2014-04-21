import os
from bbio import *

x = 0                   # holds the incoming raw data
BPM = 0                 # used to hold the pulse rate
IBI = 600               # holds the time between beats, must be seeded! 
Pulse = False           # true when pulse wave is high, false when it's low
QS = False              # becomes true when a beat is found

rate = [0] * 10         # array to hold last ten IBI values
sampleCounter = 0       # used to determine pulse timing
lastBeatTime = 0        # used to find IBI
P = 2048                # used to find peak in pulse wave, seeded
T = 2048                # used to find trough in pulse wave, seeded
thresh = 2048           # used to find instant moment of heart beat, seeded
amp = 100               # used to hold amplitude of pulse waveform, seeded
firstBeat = True        # used to seed rate array so we startup with reasonable BPM
secondBeat = False      # used to seed rate array so we startup with reasonable BPM
Pulse = False           # flag indicating pulse

ain0 = file("/sys/bus/platform/devices/tsc/ain1")
led0_1 = 'echo 1 > /sys/class/leds/beaglebone::usr0/brightness'
led0_0 = 'echo 0 > /sys/class/leds/beaglebone::usr0/brightness'
led1_1 = 'echo 1 > /sys/class/leds/beaglebone::usr1/brightness'
led1_0 = 'echo 0 > /sys/class/leds/beaglebone::usr1/brightness'
testLed = False
pdTest = 0

def setup():
    pass

def loop():
    # Sinais para teste
    if testLed:
        os.system(led1_0)
        testLed = False
    else:
        os.system(led1_1)
        testLed = True
    if pdTest == 100:
        pdTest = 0
    else:
        pdTest += 1
    sendToPD(pdTest)

    
    x = ain0.read()                             # Reads AnalogPin 1
    sendToPD(0, x, 3000)               # Sends to PD
    if QS:
        sendToPD(1, BPM, 3000)         # If there is heartbeat, send to PD
        QS = False          
    
    sampleCounter += 2
    N = sampleCounter - lastBeatTime
    
    if x < thresh and N > (IBI/5)*3:            # avoid dichrotic noise by waiting 3/5 of last IBI
        if x < T:                               # T is the trough
            T = x                               # keep track of lowest point in pulse wave 
    
    if x > thresh:                              # thresh condition helps avoid noise
        if x > P:                               # P is the peak
            P = x                               # keep track of highest point in pulse wave
            
    # Now it's time to calculate the heartbeat
    # Signal surges up in value every time there is a pulse
    if N > 250:                                 # avoid high frequency noise
        if x > thresh and Pulse == False and N > (IBI/5)*3:
            Pulse = True                        # set the Pulse flag when we think there is a pulse
            os.system(led0_1)                   # turn on led0 onboard
            IBI = sampleCounter - lastBeatTime  # measure time between beats in mS
            lastBeatTime = sampleCounter        # keep track of time for next pulse
    
        if secondBeat:                          # if this is the second beat, if secondBeat == TRUE
            secondBeat = False                  # clear secondBeat flag
            for i in range(0, 9):               # seed the running total to get a realistic BPM at startup
                rate[i] = IBI
        
        if firstBeat:                           # if it's the first time we found a beat, if firstBeat == TRUE
            firstBeat = False                   # clear firstBeat flag
            secondBeat = True                   # set the second beat flag
            return                              # IBI value is unreliable so discard it
        
        # keep a running total of the last 10 IBI values
        runningTotal = 0                        # clear the runningTotal variable
        
        for i in range(0, 8):                   # shift data in the rate array
            rate[i] = rate[i + 1]               # and drop the oldest IBI value 
            runningTotal += rate[i]             # add up the 9 oldest IBI values
            
        rate[9] = IBI                           # add the latest IBI to the rate array
        runningTotal += rate[9]                 # add the latest IBI to runningTotal
        runningTotal /= 10                      # average the last 10 IBI values 
        BPM = 60000 / runningTotal              # how many beats can fit into a minute? that's BPM!
        QS = True                               # set Quantified Self flag 
    
    if x < thresh and Pulse == True:            # when the values are going down, the beat is over
        os.system(led0_0)                       # turn off on board led0
        Pulse = False                           # reset the Pulse flag so we can do it again
        amp = P - T                             # get amplitude of the pulse wave
        thresh = amp/2 + T                      # set thresh at 50% of the amplitude
        P = thresh                              # reset these for next time
        T = thresh
    
    if N > 2500:                                # if 2.5 seconds go by without a beat
        thresh = 2048                           # set thresh default
        P = 2048                                # set P default
        T = 2048                                # set T default
        lastBeatTime = sampleCounter            # bring the lastBeatTime up to date        
        firstBeat = True                        # set these to avoid noise
        secondBeat = False                      # when we get the heartbeat back
        
    delay(2)

def sendToPD(self, channel, msg, port):
    os.system("echo '" + str(channel) + " " + str(msg) +";' | pdsend " + str(port))

run(setup, loop)