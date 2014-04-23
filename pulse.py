import os
from time import sleep

def sendToPD(self, channel, msg, port):
    os.system("echo '" + str(channel) + " " + str(msg) +";' | pdsend " + str(port))

class Looper():

    def __init__(self):
        self.x = 0                   # holds the incoming raw data
        self.BPM = 0                 # used to hold the pulse rate
        self.IBI = 600               # holds the time between beats, must be seeded! 
        self.Pulse = False           # true when pulse wave is high, false when it's low
        self.QS = False              # becomes true when a beat is found
            
        self.rate = [0] * 10         # array to hold last ten IBI values
        self.sampleCounter = 0       # used to determine pulse timing
        self.lastBeatTime = 0        # used to find IBI
        self.P = 2048                # used to find peak in pulse wave, seeded
        self.T = 2048                # used to find trough in pulse wave, seeded
        self.thresh = 2048           # used to find instant moment of heart beat, seeded
        self.amp = 100               # used to hold amplitude of pulse waveform, seeded
        self.firstBeat = True        # used to seed rate array so we startup with reasonable BPM
        self.secondBeat = False      # used to seed rate array so we startup with reasonable BPM
        self.Pulse = False           # flag indicating pulse
            
        self.ain0 = file("/sys/devices/ocp.3/helper.15/AIN0")
        self.led0_1 = 'echo 1 > /sys/class/leds/beaglebone::usr0/brightness'
        self.led0_0 = 'echo 0 > /sys/class/leds/beaglebone::usr0/brightness'
        self.led1_1 = 'echo 1 > /sys/class/leds/beaglebone::usr1/brightness'
        self.led1_0 = 'echo 0 > /sys/class/leds/beaglebone::usr1/brightness'
        self.testLed = False
        self.pdTest = 0
    
    def loop(self):
        # Test signals
        if self.testLed:
            os.system(self.led1_0)
            self.testLed = False
        else:
            os.system(self.led1_1)
            self.testLed = True
        if self.pdTest == 100:
            self.pdTest = 0
        else:
            self.pdTest += 1
        sendToPD(self.pdTest)
    
        
        self.x = self.ain0.read()                             # Reads AnalogPin 1
        sendToPD(0, self.x, 3000)               # Sends to PD
        if self.QS:
            sendToPD(1, self.BPM, 3000)         # If there is heartbeat, send to PD
            self.QS = False          
        
        self.sampleCounter += 2
        self.N = self.sampleCounter - self.lastBeatTime
        
        if self.x < self.thresh and self.N > (self.IBI/5)*3:            # avoid dichrotic noise by waiting 3/5 of last IBI
            if self.x < self.T:                               # T is the trough
                self.T = self.x                               # keep track of lowest point in pulse wave 
        
        if self.x > self.thresh:                              # thresh condition helps avoid noise
            if self.x > self.P:                               # P is the peak
                self.P = self.x                               # keep track of highest point in pulse wave
                
        # Now it's time to calculate the heartbeat
        # Signal surges up in value every time there is a pulse
        if self.N > 250:                                 # avoid high frequency noise
            if self.x > self.thresh and self.Pulse == False and self.N > (self.IBI/5)*3:
                self.Pulse = True                        # set the Pulse flag when we think there is a pulse
                os.system(self.led0_1)                   # turn on led0 onboard
                self.IBI = self.sampleCounter - self.lastBeatTime  # measure time between beats in mS
                self.lastBeatTime = self.sampleCounter        # keep track of time for next pulse
        
            if self.secondBeat:                          # if this is the second beat, if secondBeat == TRUE
                self.secondBeat = False                  # clear secondBeat flag
                for i in range(0, 9):               # seed the running total to get a realistic BPM at startup
                    self.rate[i] = self.IBI
            
            if self.firstBeat:                           # if it's the first time we found a beat, if firstBeat == TRUE
                self.firstBeat = False                   # clear firstBeat flag
                self.secondBeat = True                   # set the second beat flag
                return                              # IBI value is unreliable so discard it
            
            # keep a running total of the last 10 IBI values
            runningTotal = 0                        # clear the runningTotal variable
            
            for i in range(0, 8):                   # shift data in the rate array
                self.rate[i] = self.rate[i + 1]               # and drop the oldest IBI value 
                runningTotal += self.rate[i]             # add up the 9 oldest IBI values
                
            self.rate[9] = self.IBI                           # add the latest IBI to the rate array
            runningTotal += self.rate[9]                 # add the latest IBI to runningTotal
            runningTotal /= 10                      # average the last 10 IBI values 
            self.BPM = 60000 / runningTotal              # how many beats can fit into a minute? that's BPM!
            self.QS = True                               # set Quantified Self flag 
        
        if self.x < self.thresh and self.Pulse == True:            # when the values are going down, the beat is over
            os.system(self.led0_0)                       # turn off on board led0
            self.Pulse = False                           # reset the Pulse flag so we can do it again
            self.amp = self.P - self.T                             # get amplitude of the pulse wave
            self.thresh = self.amp/2 + self.T                      # set thresh at 50% of the amplitude
            self.P = self.thresh                              # reset these for next time
            self.T = self.thresh
        
        if self.N > 2500:                                # if 2.5 seconds go by without a beat
            self.thresh = 2048                           # set thresh default
            self.P = 2048                                # set P default
            self.T = 2048                                # set T default
            self.lastBeatTime = self.sampleCounter            # bring the lastBeatTime up to date        
            self.firstBeat = True                        # set these to avoid noise
            self.secondBeat = False                      # when we get the heartbeat back
            
        sleep(2.0/1000.0)
    


l = Looper()
l.loop()