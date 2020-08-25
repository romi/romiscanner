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
import math
from typing import List

from .units import *

class Pose():
    def __init__(self, x: Length_mm = None,
                 y: Length_mm = None,
                 z: Length_mm = None,
                 pan: Deg = None,
                 tilt: Deg = None):
        self.x = x
        self.y = y
        self.z = z
        self.pan = pan
        self.tilt = tilt

    def attributes(self):
        return ["x", "y", "z", "pan", "tilt"]

class PathElement(Pose):
    def __init__(self, x: Length_mm = None,
                 y: Length_mm = None,
                 z: Length_mm = None,
                 pan: Deg = None,
                 tilt: Deg = None,
                 exact_pose: bool = True):
        super().__init__(x, y, z, pan, tilt)
        self.exact_pose = exact_pose

    def __repr__(self):
        res = []
        for attr in self.attributes():
            if getattr(self, attr) is not None:
                res.append("%s = %.2f" % (attr, getattr(self, attr)))
        return ", ".join(res)

class Path(List[PathElement]):
    def __init__(self):
        self = list()

class Circle(Path):
    def __init__(self, center_x: Length_mm, center_y: Length_mm, z: Length_mm, tilt: Deg, radius: Length_mm,
                 n_points: int):
        super().__init__()
        for i in range(n_points):
            pan = 2 * i * math.pi / n_points
            x = center_x - radius * math.cos(pan)
            y = center_y - radius * math.sin(pan)
            pan = pan * 180 / math.pi
            pan = (pan - 90) % 360
            self.append(PathElement(x, y, z, pan, tilt, exact_pose=False))

class Cylinder(Path):
    def __init__(self, center_x: Length_mm, center_y: Length_mm, z_range: (Length_mm, Length_mm),
                 tilt: Deg, radius: Length_mm, n_points: int, n_circles=2):
        super().__init__()
        min_z, max_z = z_range
        for z_circle in range(min_z, max_z + 1, int((max_z - min_z) / (n_circles - 1))):
            for i in range(n_points):
                pan = 2 * i * math.pi / n_points
                x = center_x - radius * math.cos(pan)
                y = center_y - radius * math.sin(pan)
                pan = pan * 180 / math.pi
                pan = (pan - 90) % 360
                self.append(PathElement(x, y, z_circle, pan, tilt, exact_pose=False))

class Line(Path):
    def __init__(self, x_0: Length_mm, y_0: Length_mm, z_0: Length_mm,
                 x_1: Length_mm, y_1: Length_mm, z_1: Length_mm,
                 pan: Deg, tilt: Deg,
                 n_points: int):
        for i in range(n_points):
            self.append(PathElement(x=(1 - i / (n_points - 1)) * x_0 + (i / (n_points - 1)) * x_1,
                                    y=(1 - i / (n_points - 1)) * y_0 + (i / (n_points - 1)) * y_1,
                                    z=(1 - i / (n_points - 1)) * z_0 + (i / (n_points - 1)) * z_1),
                                    pan=pan, tilt=tilt, exact_pose=True)

class CalibrationScan(Path):
    def __init__(self, path: Path, n_points_line: int):
        el0 = path[0]
        el1 = path[len(path) // 4 - 1]
        self = Line(el0.x, el0.y, el0.z, el0.x, el1.y, el0.z, el0.pan, el0.tilt)
        self.extend(path)
