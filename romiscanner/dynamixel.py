#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# romiscanner - Python tools for the ROMI 3D Scanner
#
# Copyright (C) 2018 Sony Computer Science Laboratories
# Authors: D. Colliaux, T. Wintz, P. Hanappe
#
# This file is part of romiscanner.
#
# romiscanner is free software: you can redistribute it
# and/or modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# romiscanner is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with romiscanner.  If not, see
# <https://www.gnu.org/licenses/>.

import pyxl430 as xl430
from romiscanner import hal, error
import time
import math
import atexit


STEPS_PER_TURN = 4096

class Gimbal(hal.AbstractGimbal):
    def __init__(self,
        dev: str = "/dev/ttyUSB1",
        baud_rate: int=1000000,
        pan_id: int=1, tilt_id: int=2, pan0: int=0, tilt0: int=1024):

        self.baud_rate = baud_rate
        self.dev = dev
        self.port = xl430.USB2Dynamixel(dev)
        self.port.start(baud_rate) #Start USB serial connection
        self.pan_zero = pan0
        self.tilt_zero = tilt0
        self.pan_id = pan_id
        self.tilt_id = tilt_id
        self.start()
        atexit.register(self.stop)

    def start(self) -> None:
        self.port.start(self.baud_rate) #Start USB serial connection
        self.pan = xl430.Actuator(self.port, self.pan_id)
        self.tilt = xl430.Actuator(self.port, self.tilt_id)
        self.pan.set_torque_enable(False)
        self.tilt.set_torque_enable(False)
        self.pan.set_operating_mode(3)
        self.tilt.set_operating_mode(3)
        self.pan.set_torque_enable(True)
        self.tilt.set_torque_enable(True)

    def home(self) -> None:
        pass
        
    def stop(self) -> None:
        self.port.stop()
        
    def get_position(self) -> Tuple[Deg, Deg]:
        pan = self.pan.get_present_position()
        tilt = self.tilt.get_present_position()
        return [self.__pan_step2angle(pan), self.__tilt_step2angle(tilt)]

    def async_enabled(self) -> bool:
        return True
    
    def moveto_async(self, pan: Deg, tilt: Deg) -> None:
        """
        Move to given angles (in degrees)
        """
        pan = self.__pan_angle2steps(pan)
        tilt = self.__tilt_angle2steps(tilt)
        self.pan.set_goal_position(pan)
        self.tilt.set_goal_position(tilt)

    
    def moveto(self, pan: Deg, tilt: Deg) -> None:
        """
        Move to given angles (in degrees)
        """
        self.moveto_async(pan, tilt)
        self.wait()
        
    
    def wait(self):
        while self.pan.is_moving() or self.tilt.is_moving():
            time.sleep(0.01)

        
    def __pan_angle2steps(self, angle):
        return int(STEPS_PER_TURN * angle / 360. + self.pan_zero)

    def __tilt_angle2steps(self, angle):
        return int(STEPS_PER_TURN * angle / 360. + self.tilt_zero)

    def __pan_step2angle(self, steps):
        return (steps - self.pan_zero) * 360. / STEPS_PER_TURN

    def __tilt_step2angle(self, steps):
        return (steps - self.tilt_zero) * 360. / STEPS_PER_TURN
    
def set_baud_rate(rate, dev = "/dev/ttyUSB1"):
    usb = xl430.USB2Dynamixel(dev)
    usb.start() #Start USB serial connection

    pan = xl430.Actuator(usb, 1) # get the motor with id 1
    pan.set_torque_enable(False) # deactivate motor
    print("baud rate %d" % pan.get_baud_rate())
    pan.set_baud_rate(rate)

    tilt = xl430.Actuator(usb, 2) # get the motor with id 2
    tilt.set_torque_enable(False) # deactivate motor
    print("baud rate %d" % tilt.get_baud_rate())
    tilt.set_baud_rate(rate)

    
def get_baud_rate(rate, dev = "/dev/ttyUSB1"):
    usb = xl430.USB2Dynamixel(dev)
    usb.start(1000000)

    pan = xl430.Actuator(usb, 1) # get the motor with id 1
    pan.set_torque_enable(False) # deactivate motor
    print("baud rate (pan): %d" % pan.get_baud_rate())

    tilt = xl430.Actuator(usb, 2) # get the motor with id 2
    tilt.set_torque_enable(False) # deactivate motor
    print("baud rate (tilt): %d" % tilt.get_baud_rate())
