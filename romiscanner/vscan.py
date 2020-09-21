# !/usr/bin/env python3
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

import atexit
import json
import os
import random
import socket
import subprocess
import tempfile
import time
from io import BytesIO
from typing import List

import imageio
import numpy as np
import psutil
import requests
from romidata import io
from romidata.db import File
from romiscanner import path
from romiscanner.hal import DataItem, AbstractScanner

from .log import logger



def check_port(port: str):
    """ True -- it's possible to listen on this port for TCP/IPv4 or TCP/IPv6
    connections. False -- otherwise.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', port))
        sock.listen(5)
        sock.close()
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.bind(('::1', port))
        sock.listen(5)
        sock.close()
    except socket.error as e:
        return False
    return True

class VirtualScannerRunner():
    """
    A class for running blender in the background for the virtual scanner. It initalizes the flask server
    on a random port between 9000 and 9999 and then listens http requests on that port. The process
    is started with the start() method and stopped with the stop() method.
    """
    def __init__(self, scene: str=None):
        self.process = None
        self.scene = scene

    def start(self):
        port = 0
        while True:
            port = random.randint(9000, 9999)
            if check_port(port):
                break
        self.port = port

        proclist = ["romi_virtualscanner", "--", "--port", str(self.port)]
        if self.scene is not None:
            logger.debug("scene = %s"%self.scene)
            proclist.extend(['--scene', self.scene])
        self.process = subprocess.Popen(proclist)
        atexit.register(VirtualScannerRunner.stop, self)
        while True:
            try:
                x = requests.get("http://localhost:%i"%self.port)
                break
            except:
                logger.debug("Virtual scanner not ready yet...")
                time.sleep(1)
                continue

    def stop(self):
        print("killing blender...")
        parent_pid = self.process.pid
        parent = psutil.Process(parent_pid)
        for child in parent.children(recursive=True):  # or parent.children() for recursive=False
            child.kill()
        parent.kill()
        while True:
            if self.process.poll() != None:
                break
            time.sleep(1)

class VirtualScanner(AbstractScanner):
    def __init__(self, width: int, # image width
                       height: int, # image height
                       focal: float, # camera focal
                       flash: bool=False, # light the scene with a flash
                       host: str=None, # host port, if None, launches a virtual scanner process
                       port: int= 5000, # port, useful only if host is set
                       scene: str=None,
                       add_leaf_displacement: bool=False,
                       classes: List[str]=[]): # list of classes to render
        super().__init__()

        if host == None:
            self.runner = VirtualScannerRunner(scene=scene)
            self.runner.start()
            self.host= "localhost"
            self.port = self.runner.port
        else:
            self.runner = None
            self.host = host
            self.port = port

        self.path = []
        self.classes = classes

        self.flash = flash
        self.set_intrinsics(width, height, focal)
        self.id = 0
        self.ext = "png"
        self.position = path.Pose()
        self.add_leaf_displacement = add_leaf_displacement
        logger.warning(self.add_leaf_displacement)

    def get_position(self) -> path.Pose:
        return self.position

    def set_position(self, pose: path.Pose) -> None:
        data = {
            "rx": 90 - pose.tilt,
            "rz": pose.pan,
            "tx": pose.x,
            "ty": pose.y,
            "tz": pose.z
        }
        self.request_post("camera_pose", data)
        self.position = pose

    def set_intrinsics(self, width: int, height: int, focal: float) -> None:
        self.width = width
        self.height = height
        self.focal = focal
        data = {
            "width": width,
            "height": height,
            "focal": focal,
        }
        self.request_post("camera_intrinsics", data)

    def list_objects(self):
        return self.request_get_dict("objects")

    def list_backgrounds(self):
        return self.request_get_dict("backgrounds")

    def load_object(self, file, mtl=None, palette=None, colorize=True):
        """
        Loads an object from a OBJ file and a palette image.
        """
        if type(file) == str:
            file = io.dbfile_from_local_file(file)
        if type(mtl) == str:
            mtl = io.dbfile_from_local_file(mtl)
        if type(palette) == str:
            palette = io.dbfile_from_local_file(palette)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, file.filename)
            io.to_file(file, file_path)
            files = { "file" : open(file_path, "rb")}
            if mtl is not None:
                mtl_file_path = os.path.join(tmpdir, mtl.filename)
                io.to_file(mtl, mtl_file_path)
                files["mtl"] = open(mtl_file_path, "rb")
            if palette is not None:
                palette_file_path = os.path.join(tmpdir, palette.filename)
                io.to_file(palette, palette_file_path)
                files["palette"] = open(palette_file_path, "rb")
            res = self.request_post("upload_object", {"colorize" : colorize}, files)
        if self.add_leaf_displacement:
            self.request_get_dict("add_random_displacement/leaf")
        return res

    def load_background(self, file: File):
        """
        Loads a background from a HDRI file
        """
        logger.debug("loading background : %s"%file.filename)
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, file.filename)
            io.to_file(file, file_path)
            files = { "file" : open(file_path, "rb")}
            return self.request_post("upload_background", {}, files)

    def request_get_bytes(self, endpoint: str) -> bytes:
        x = requests.get("http://%s:%s/%s"%(self.host, self.port, endpoint))
        if x.status_code != 200:
            raise Exception("Unable to connect to virtual scanner (code %i)"%x.status_code)
        return x.content

    def request_get_dict(self, endpoint: str) -> dict:
        b = self.request_get_bytes(endpoint)
        return json.loads(b.decode())

    def request_post(self, endpoint: str, data: dict, files: dict=None) -> None:
        x = requests.post("http://%s:%s/%s"%(self.host, self.port, endpoint), data=data, files=files)
        if x.status_code != 200:
            raise Exception("Virtual scanner returned an error (error code %i)"%x.status_code)

    def channels(self):
        if self.classes == []:
            return ['rgb']
        else:
            return ['rgb'] + self.classes + ['background']

    def get_bounding_box(self):
        return self.request_get_dict("bounding_box")

    def grab(self, idx: int, metadata: dict=None) -> DataItem:

        data_item = DataItem(idx, metadata)
        for c in self.channels():
            if c != 'background':
                data_item.add_channel(c, self.render(channel=c))
            else:
                x = np.zeros(data_item.channel(self.classes[0]).data.shape)
                for c in self.classes:
                    x = np.maximum(x, data_item.channel(c).data)
                x = 1.0 - x
                data_item.add_channel("background", x)
                
        rt = self.request_get_dict("camera_pose")
        k = self.request_get_dict("camera_intrinsics")

        if metadata is None:
            metadata = {}

        metadata["camera"] = {
            "camera_model" : k,
            **rt
        }
        return data_item
                
    def render(self, channel='rgb'):
        if channel == 'rgb':
            ep = "render"
            if self.flash:
                ep = ep+"?flash=1"
            x = self.request_get_bytes(ep)
            data = imageio.imread(BytesIO(x))
            return data
        else:
            x = self.request_get_bytes("render_class/%s"%channel)
            data = imageio.imread(BytesIO(x))
            data = data[:,:,3]
            return data
