import socket
import json
import random
import subprocess
import os
import signal
import psutil
import atexit
import time
import requests
import imageio
from io import BytesIO
import numpy as np
from typing import List
import tempfile

from romidata.db import Fileset, File

from romiscanner import scan
from romiscanner.hal import DataItem, AbstractScanner
from romiscanner import path
from romidata import io


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
    def __init__(self, data_dir: str="data",
                       hdri_dir: str="hdri"):
        self.process = None
        self.data_dir = data_dir
        self.hdri_dir = hdri_dir

    def start(self):
        port = 0
        while True:
            port = random.randint(9000, 9999)
            if check_port(port):
                break
        self.port = port
        self.process = subprocess.Popen(["romi_virtualscanner", "--", "--port", str(port),
                            "--data-dir", str(self.data_dir), "--hdri-dir", str(self.hdri_dir)])
        atexit.register(VirtualScannerRunner.stop, self)
        time.sleep(2)

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
                       classes: List[str]=[], # list of classes to render
                       obj: str= None,
                       background: str=None):
        super().__init__()
        if host == None:
            self.runner = VirtualScannerRunner()
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
        self.position = path.Pose()

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

    def load_object(self, file: File, palette: File=None):
        """
        Loads an object from a OBJ file and a palette image.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, file.filename)
            io.to_file(file, file_path)
            files = { "file" : open(file_path, "rb")}
            if palette is not None:
                palette_file_path = os.path.join(tmpdir, palette.filename)
                io.to_file(palette, palette_file_path)
                files["palette"] = open(palette_file_path, "rb")
            return self.request_post("upload_object", {}, files)

    def load_background(self, file: File):
        """
        Loads a background from a HDRI file
        """
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
        return ['rgb'] + self.classes

    def grab(self, idx: int, metadata: dict=None) -> DataItem:
        data_item = DataItem(idx, metadata)
        for c in self.channels():
            data_item.add_channel(c, self.render(channel=c))
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
            return data