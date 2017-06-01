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

    def scanAt(self, x, y, z, pan, tilt, i, dt=2):
        cnc.move_to(x, y, z)
        bracket.move_to(pan, tilt)
        time.sleep(dt)
        camera.grab_data(self.scandir, i)
        return

    def circularscan(self, xc, yc, zc, r, nc, svg="all.zip"):
       self.files = []
       traj=[]
       x, y, pan = scanpath.circle(xc, yc, r, nc)
       for i in range(0, nc):
         xi, yi, zi = self.xyz_clamp(x[i], y[i], zc)
         pi, ti  = self.pantilt_clamp(pan[i], self.bracket.tilt)
         traj.append([xi,yi,zi,pi,ti])
         self.scanAt(x, y, z, pi, ti, i)
       
       self.cnc.move_to(x[0], y[0], zc)
       self.bracket.move_to(0, self.bracket.tilt)
       np.save(np.asarray(traj),scandir+"traj")
       ut.createArchive(scandir, svg)
       
    def get_position(self):
       return {'x': self.cnc.x, 'y': self.cnc.y, 'z': self.cnc.z, 'pan': self.bracket.pan, 'tilt': self.bracket.tilt }

    def xyz_clamp(self, x, y, z):
       return ut.clamp(x, self.cnc.x_lims), ut.clamp(y, self.cnc.y_lims), ut.clamp(z, self.cnc.z_lims)

    def pantilt_clamp(self, pan, tilt):
       return ut.clamp(pan, self.bracket.pan_lims), ut.clamp(tilt, self.bracket.tilt_lims)
