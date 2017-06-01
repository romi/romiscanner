#!/usr/bin/python
from hardware import cartesian_arm, rotation_unit, camera
from motion_planning import scanpath  
import utils as ut

class Robot(object):
    def __init__(self, scandir, x=0, y=0, z=0, pan=0, tilt=0):
        self.cnc     = cartesian_arm.CNC(port="/dev/ttyUSB0",x=x, y=y, z=z,homing=True)
        self.bracket = rotation_unit.RotatingUnit(port="/dev/ttyACM0",pan=pan, tilt=tilt)
        self.cam     = camera.Camera()
        self.scandir = scandir
        self.files   = [] #not sure it belongs there  

    def scanAt(self, x, y, z, pan, tilt, i, files):
        cnc.move_to(x, y, z)
        bracket.move_to(pan, tilt)
        time.sleep(2)
        rgb = "rgb-%03d.png"%i
        depth = "depth-%03d.png"%i
        grab_images(scandir + rgb,
                    scandir + depth)
        self.files.append({"href": "scan/" + rgb,
                      "name": rgb})
        self.files.append({"href": "scan/" + depth,
                      "name": depth})
        return

    def circularscan(self, xc, yc, zc, r, nc):
       self.files = []    
       x, y, pan = scanpath.circle(xc, yc, r, nc)
       for i in range(0, nc):
         self.scanAt(x[i], y[i], zc, pan[i], self.bracket.tilt, i)
       cnc.move_to(x[0], y[0], zc)
       bracket.move_to(0, selftilt)
       self.files.append(ut.createArchive(self.files))
       
    def get_position(self):
       return {'x': self.cnc.x, 'y': self.cnc.y, 'z': self.cnc.z, 'pan': self.bracket.pan, 'tilt': self.bracket.tilt }

    def xyz_clamp(self, x, y, z):
       return ut.clamp(x, self.cnc.x_lims), ut.clamp(y, self.cnc.y_lims), ut.clamp(z, self.cnc.z_lims)

    def pantilt_clamp(self, pan, tilt):
       return ut.clamp(pan, self.bracket.pan_lims), ut.clamp(tilt, self.bracket.tilt_lims)