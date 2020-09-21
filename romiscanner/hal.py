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

from abc import ABC, ABCMeta, abstractmethod
import numpy as np

from .units import *
from . import path
from typing import Tuple, List
from romidata.db import Fileset
from romidata import io
import logging

logger = logging.getLogger("romiscanner")


class ChannelData():
    def __init__(self, name: str, data: np.array, idx: int):
        self.data = data
        self.idx = idx
        self.name = name

    def format_id(self):
        return "%05d_%s"%(self.idx, self.name)

class DataItem():
    def __init__(self, idx: int, metadata=None):
        self.channels = {}
        self.metadata = metadata
        self.idx = idx

    def add_channel(self, channel_name: str, data: np.array) -> None:
        self.channels[channel_name] = ChannelData(channel_name, data, self.idx)

    def channel(self, channel_name: str) -> ChannelData:
        return self.channels[channel_name]

class AbstractCNC(metaclass=ABCMeta):
    def __init__(self):
        pass

    @abstractmethod    
    def home(self) -> None:
        pass

    @abstractmethod    
    def get_position(self) -> Tuple[Length_mm, Length_mm, Length_mm]:
        pass

    @abstractmethod    
    def moveto(self, x: Length_mm, y: Length_mm, z: Length_mm) -> None:
        pass

    @abstractmethod    
    def async_enabled(self):
        pass

    @abstractmethod    
    def moveto_async(self, x: Length_mm, y: Length_mm, z: Length_mm) -> None:
        pass

    @abstractmethod    
    def wait(self) -> None:
        pass

class AbstractGimbal(ABC):
    @abstractmethod
    def has_position_control(self) -> bool:
        pass

    @abstractmethod
    def get_position(self) -> Tuple[Deg, Deg]:
        pass

    @abstractmethod
    def moveto(self, pan: Deg, tilt: Deg) -> None:
        pass

    @abstractmethod
    def async_enabled(self) -> bool:
        pass

    @abstractmethod
    def moveto_async(self, pan: Deg, tilt: Deg) -> None:
        pass

    @abstractmethod
    def wait(self) -> None:
        pass

    
class AbstractCamera():
    @abstractmethod
    def grab(self, idx: int, metadata: dict=None):
        pass

    @abstractmethod
    def channels(self):
        pass


class AbstractScanner(metaclass=ABCMeta):
    def __init__(self):
        self.scan_count = 0
        self.ext = 'jpg'
        super().__init__()

    @abstractmethod
    def get_position(self) -> path.Pose:
        pass

    @abstractmethod
    def set_position(self, pose: path.Pose) -> None:
        pass

    @abstractmethod
    def grab(self, idx:int, metadata: dict) -> DataItem:
        pass

    @abstractmethod
    def channels(self) -> List[str]:
        pass

    def inc_count(self) -> int:
        x = self.scan_count
        self.scan_count += 1
        return x

    def get_target_pose(self, x : path.PathElement) -> path.Pose:
        pos = self.get_position()
        target_pose = path.Pose()
        for attr in pos.attributes():
            if getattr(x, attr) is None:
                setattr(target_pose, attr, getattr(pos, attr))
            else:
                setattr(target_pose, attr, getattr(x, attr))
        return target_pose 

    def scan(self, path: path.Path, fileset: Fileset) -> None:
        for x in path:
            pose = self.get_target_pose(x)
            print(pose)
            data_item = self.scan_at(pose, x.exact_pose)
            for c in self.channels():
                f = fileset.create_file(data_item.channels[c].format_id())
                io.write_image(f, data_item.channels[c].data, ext=self.ext)
                if data_item.metadata is not None:
                    f.set_metadata(data_item.metadata)
                f.set_metadata("shot_id", "%06i"%data_item.idx) 
                f.set_metadata("channel", c) 
    
    def scan_at(self, pose: path.Pose, exact_pose: bool=True, metadata: dict={}) -> DataItem:
        logger.debug("scanning at")
        logger.debug(pose)
        if exact_pose:
            metadata = {**metadata, "pose": [pose.x,pose.y,pose.z,pose.pan,pose.tilt]}
        else:
            metadata = {**metadata, "approximate_pose": [pose.x,pose.y,pose.z,pose.pan,pose.tilt]}
        logger.debug(metadata)
        self.set_position(pose)
        return self.grab(self.inc_count(), metadata=metadata)
