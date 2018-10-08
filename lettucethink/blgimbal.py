
import serial
import json
import time
import math
import numpy as np
from lettucethink import hal, error

STEPS_PER_TURN = 50
ZERO_PAN=0
ZERO_TILT=2

# cmp() is no longer defined in Python3 (silly)
def cmp(a, b):
    return (a > b) - (a < b)

class Gimbal(hal.CNC):
    def __init__(self, port="/dev/ttyUSB0"):
        self.port = port
        self.status = "idle"
        self.p = [0, 0]
        self.v = [0, 0]
        self.serial_port = None
        self.start()

        
    def start(self):
        self.serial_port = serial.Serial(self.port, 115200)
        # TODO: read '#ready' ?
        while self.serial_port.in_waiting == 0:
            time.sleep(0.1)
        self.serial_port.readline()
        self.update_status()

    def stop(self):
        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None

        
    def has_position_control():
        return True

    
    def async_enabled(self):
        return True

    
    def get_position(self):
        self.update_status()
        return self.p

    
    def has_velocity_control():
        return True

    
    def get_velocity(self):
        self.update_status()
        return self.v
   
      
       
    def get_status(self):
        self.update_status()
        return self.status

    
    def moveat(self, vpan, vtilt):
        self.__send("x%d" % vpan)
        self.__send("y%d" % vtilt)

        
    def set_target_pos(self, pan, tilt):
        self.__send("X%d" % ZERO_PAN + int(pan / 2 / math.pi * STEPS_PER_TURN))
        self.__send("Y%d" % ZERO_TILT + int(tilt / 2 / math.pi * STEPS_PER_TURN))


    def wait(self):
        time.sleep(0.1)   
        self.update_status()
        while self.status == "moving":
            time.sleep(0.1)   
            self.update_status()

        
    def moveto(self, pan, tilt):
        self.moveto_async(pan, tilt)
        self.wait()
        
        
    def moveto_async(self, pan, tilt):
        self.set_target_pos(pan, tilt)
       
            
    def update_status(self):
        v = self.__send("v").decode('utf-8')
        p = self.__send("p").decode('utf-8')
        p = p.split(":")[-1].split(",")
        v = v.split(":")[-1].split(",")
        print(p)
        self.p[0] = (int(p[0]) - ZERO_PAN) / STEPS_PER_TURN * math.pi * 2
        self.p[1] = (int(p[1]) - ZERO_TILT) / STEPS_PER_TURN * math.pi * 2
        print("p="+ str(self.p))
        self.v[0] = int(v[0])
        self.v[1] = int(v[1])
        if self.v[0] != 0 or self.v[1] != 0:
            self.status = "moving"
        else:
            self.status = "idle"
        
    def __send(self, s):
        if not self.serial_port:
            raise Error("CNC has not been started")
        r = False
        try:
            self.serial_port.write(bytes('%s\n' % s, 'utf-8'))
            time.sleep(0.01)   
            r = self.serial_port.readline()
        finally:
            pass # dummy statement to avoid empty 'finally' clause
        if r == False:
            print('cmd=%s: failed' % (s))
        return r;