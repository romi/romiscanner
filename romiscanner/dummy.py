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

    romiscanner is distributed in the hope that it will be
    useful, but WITHOUT ANY WARRANTY; without even the implied
    warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
    See the GNU General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with romiscanner.  If not, see
    <https://www.gnu.org/licenses/>.

"""    
from romiscanner import hal, log
import time
import imageio
import numpy as np

class CNC(hal.AbstractCNC):
    '''
    CNC functionalities 
    TODO: enable workspace origin offset, motor seed configuration,...
    '''
    def __init__(self):
        self.position = (0., 0., 0.)

    def start(self, homing=False):
        pass

    def stop(self):
        pass

    def home(self):
        pass
            
    def get_position(self):
        return self.position

    def async_enabled(self):
        return True
                    
    def moveto(self, x, y, z):
        self.position[0] = x
        self.position[1] = y
        self.position[2] = z
    
    def moveto_async(self, x, y, z):
        self.position[0] = x
        self.position[1] = y
        self.position[2] = z
        
    def wait(self):
        pass


class Gimbal(hal.AbstractGimbal):
    def __init__(self):
        self.position = (0., 0.)

    def start(self, homing=False):
        pass

    def stop(self):
        pass

    def home(self):
        pass
            
    def get_position(self):
        return self.position

    def async_enabled(self):
        return True
                    
    def moveto(self, pan, tilt):
        self.position[0] = pan
        self.position[1] = tilt
    
    def moveto_async(self, x, y, z):
        self.position[0] = pan
        self.position[1] = tilt
        
    def wait(self):
        pass
    


class Camera(hal.AbstractCamera):
    def __init__(self, path: str=None):
        self.path = path
        if path is not None:
            self.image = imageio.imread(self.path)
        else:
            self.image = np.rand(10, 10, 3)

    def channels(self):
        return ["rgb"]

    def grab(self, idx: int, metadata: dict=None):
        data_item = DataItem(idx, metadata)
        data_item.add_channel("rgb", self.image)
        return data_item

