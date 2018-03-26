#!/usr/bin/env python3
from hardware import cartesian_arm, rotation_unit, camera
from motion_planning import scanpath  
import utils as ut
import time
import numpy as np
import os

class Robot(object):
    def __init__(self, scandir, x=0, y=0, z=0, pan=0, tilt=0, homing=True):
        self.cnc     = cartesian_arm.CNC(port="/dev/ttyUSB0",x=x, y=y, z=z,homing=homing)
        self.bracket = rotation_unit.RotationUnit(port="/dev/ttyACM0",pan=pan, tilt=tilt, homing=homing)
        self.cam     = camera.Camera()
        self.scandir = scandir

    def scanAt(self, x, y, z, pan, tilt, i, dt=2):
        self.cnc.moveto(x, y, z)
        self.bracket.moveto(pan, tilt)
        time.sleep(dt)
        self.cam.grab_data(self.scandir, i)
        return

    def circularscan(self, xc, yc, zc, r, nc, svg="all.zip"):
        self.files = []
        traj=[]
        x, y, pan = scanpath.circle(xc, yc, r, nc)
        pan=-pan        
        for i in range(0, nc):
           xi, yi, zi = self.xyz_clamp(x[i], y[i], zc)
           pi, ti  = self.pantilt_clamp(pan[i], self.bracket.tilt)
           traj.append([xi,yi,zi,pi,ti])
           self.scanAt(xi, yi, zi, pi, ti, i)
       
        self.cnc.moveto(x[0], y[0], zc)
        self.bracket.moveto(0, self.bracket.tilt)
        np.save(self.scandir+"traj", np.asarray(traj))
        ut.createArchive(self.scandir, svg)
 
    def get_position(self):
        return {'x': self.cnc.x, 'y': self.cnc.y, 'z': self.cnc.z, 'pan': self.bracket.pan, 'tilt': self.bracket.tilt }

    def xyz_clamp(self, x, y, z):
        return ut.clamp(x, self.cnc.x_lims), ut.clamp(y, self.cnc.y_lims), ut.clamp(z, self.cnc.z_lims)

    def pantilt_clamp(self, pan, tilt):
        return ut.clamp(pan, self.bracket.pan_lims), ut.clamp(tilt, self.bracket.tilt_lims)
