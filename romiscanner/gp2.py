"""

    romiscanner - Python tools for the ROMI 3D Scanner

    Copyright (C) 2018 Sony Computer Science Laboratories
    Authors: D. Colliaux, T. Wintz, P. Hanappe
  
    This file is part of romiscanner.

    romiscanner is free software: you can redistribute it
    and/or modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation, either
    version 3 of the License, or (at your option) any later version.

    romiscanner is distributed in the hope that it will be
    useful, but WITHOUT ANY WARRANTY; without even the implied
    warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
    See the GNU General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with romiscanner.  If not, see
    <https://www.gnu.org/licenses/>.

"""
import gphoto2 as gp
import os
import imageio
import tempfile
import atexit

from romiscanner import hal, error
from .hal import DataItem

class Camera(hal.AbstractCamera):
    """
    Gphoto2 Camera object.
    """

    def __init__(self):
        self.camera = None
        self.start()
        atexit.register(self.stop)

    def start(self):
        self.camera = gp.Camera()
        self.camera.init()
        cfg = self.camera.get_config()
        cmode = cfg.get_child_by_name("capturemode")
        cmode.set_value(cmode.get_choice(0))  # should put in single shot mode
        self.is_started = True

    def stop(self):
        self.camera.exit()
        self.camera = None

    def channels(self):
        return ['rgb']

    def grab(self, idx: int, metadata: dict=None):
        with tempfile.TemporaryDirectory as tmp:
            fname = os.path.join(tmp, "frame.jpg")
            self.grab_write(fname)
            data_item = DataItem(idx, metadata)
            data = imageio.imread(fname)
            data_item.add_channel("rgb", data)
            return data_item

    def grab_write(self, target: str):
        file_path = self.camera.capture(0)
        camera_file = self.camera.file_get(file_path.folder, file_path.name,
                                           gp.GP_FILE_TYPE_NORMAL)
        gp.check_result(gp.gp_file_save(camera_file, target))
        return target
