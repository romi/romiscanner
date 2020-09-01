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
import os
import imageio
import requests
import time
import json
import subprocess
import numpy as np
from io import BytesIO
from enum import Enum

from PIL import Image

from . import hal, error
from .hal import DataItem
import tempfile
from .units import *

CAMERA_FUNCTION_SHOOT = 'Remote Shooting'
CAMERA_FUNCTION_TRANSFER = 'Contents Transfer'

class SonyCamError(Exception):
    def __init__(self, message):
        self.message = message

class SonyCamAPI(object):
    def __init__(self, device_ip, api_port, timeout=2):
        self.device_ip = device_ip
        self.api_port = api_port
        self.api_url = 'http://' + device_ip + ':' + api_port + '/sony/'
        self.timeout = timeout
        method_types = self.get_method_types()
        self.supported_methods = [x[0] for x in method_types]

    def api_call(self, endpoint, method, params=[], version='1.0'):
        request_result = requests.post(self.api_url + endpoint,
                                       data=json.dumps({
                                           'method': method,
                                           'params': params,
                                           'id': 1,
                                           'version': version
                                       }),
                                       timeout=self.timeout)
        res = json.loads(request_result.content.decode('utf-8'))
        if 'error' in res:
            err = res['error']
            raise SonyCamError('''
            Failed camera request.
            Exception code: %d
            Description: %s
            ''' % (err[0], err[1]))
        if 'result' in res:
            return res['result']
        if 'results' in res:
            return res['results']
        return {}

    def start_rec_mode(self):
        return self.api_call("camera", "startRecMode")

    def take_picture(self):
        while True:
            status = self.get_camera_status()
            if status == 'ContentsTransfer':
                raise SonyCamError('Camera is in content transfer mode, cannot take picture')
            elif status == 'IDLE':
                break
            else:
                time.sleep(0.1)

        return self.api_call("camera", "actTakePicture")[0]

    def get_available_camera_function(self):
        return self.api_call("camera", "getAvailableCameraFunction")[0]

    def get_camera_function(self):
        return self.api_call("camera", "getCameraFunction")[0]

    def set_camera_function(self, function):
        return self.api_call("camera", "setCameraFunction", [function])[0]

    def get_storage_information(self):
        return self.api_call("camera", "getStorageInformation")[0]

    def get_source_list(self):
        return self.api_call("avContent", "getSourceList", [{"scheme": "storage"}])[0]

    def get_content_list(self, count, uri, stIdx=0, view="flat", sort="descending"):
        return self.api_call("avContent", "getContentList", [{
            "uri": uri,
            "stIdx": stIdx,
            "cnt": count,
            "view": view,
            "sort": sort}], version="1.3")[0]

    def get_camera_status(self):
        events = self.get_event()
        for x in events:
            if 'cameraStatus' in x:
                return x['cameraStatus']
        raise SonyCamError('Could not get camera status')

    def get_available_api_list(self):
        return self.api_call("camera", "getAvailableApiList")[0]

    def get_method_types(self, version="1.0"):
        return self.api_call("camera", "getMethodTypes", [version])

    def get_event(self, long_polling=False, version="1.0"):
        return self.api_call("camera", "getEvent", [long_polling], version=version)

    def start_shoot_mode(self):
        if ('setCameraFunction' in self.supported_methods and
                'getCameraFunction' in self.supported_methods):
            camera_function = self.get_camera_function()
            if camera_function != CAMERA_FUNCTION_SHOOT:
                self.set_camera_function(CAMERA_FUNCTION_SHOOT)
        if 'startRecMode' in self.supported_methods:
            self.start_rec_mode()
        while not self.get_camera_status() == 'IDLE':
            continue

    def setup_camera(self, params):
        if 'FNumber' in params:
            self.api_call('camera', 'setFNumber', [params['FNumber']])
        if 'ShutterSpeed' in params:
            self.api_call('camera', 'setShutterSpeed', [params['ShutterSpeed']])
        if 'IsoSpeedRate' in params:
            self.api_call('camera', 'setIsoSpeedRate', [params['IsoSpeedRate']])
        if 'WhiteBalance' in params:
            self.api_call('camera', 'setWhiteBalance', [params['WhiteBalance']])
        if 'FlashMode' in params:
            self.api_call('camera', 'setFlashMode', [params['FlashMode']])
        if 'FocusMode' in params:
            self.api_call('camera', 'setFocusMode', [params['FocusMode']])

    def start_transfer_mode(self):
        if ('setCameraFunction' in self.supported_methods and
                'getCameraFunction' in self.supported_methods):
            camera_function = self.get_camera_function()
            if camera_function != CAMERA_FUNCTION_TRANSFER:
                self.set_camera_function(CAMERA_FUNCTION_TRANSFER)
        while not self.get_camera_status() == 'ContentsTransfer':
            continue

    def get_available_shoot_mode(self):
        return self.api_call("camera", "getAvailableShootMode")[1]

    def set_shoot_mode(self, mode):
        return self.api_call("camera", "setShootMode", [mode])

    def start_movie_rec(self):
        return self.api_call("camera", "startMovieRec")

    def stop_movie_rec(self):
        return self.api_call("camera", "stopMovieRec")

    def adb_transfer_pictures(self, count=1):
        """
        Transfer the latest count pictures from the camera
        ADB shell must be enabled on the camera
        """
        subprocess.run(['adb', 'connect', self.device_ip])
        x = subprocess.run(['adb', 'shell', 'ls /sdcard/DCIM/100MSDCF'], capture_output=True)
        files = x.stdout.split()
        files = list(map(lambda x: x.decode(), files))
        files.sort()
        files = files[-count:]
        images = []
        for f in files:
            subprocess.run(['adb', 'pull', '/sdcard/DCIM/100MSDCF/' + f, '/tmp/'])
            im = imageio.imread('/tmp/' + f)
            images.append(im)
            print(f)
        return images

class FlashAirAPIError(Exception):
    def __init__(self, message):
        self.message = message

class FlashAirAPI(object):
    def __init__(self, host):
        self.host = host
        self.commands_format = "http://%s/command.cgi?%s"
        self.delete_format = "http://%s/upload.cgi?DEL=%s"
        self.path_format = "http://%s%s"
        requests.get(self.path_format % (self.host, "/"))

    def format_datetime(self, date, time):
        return date + time  # TODO

    def format_attribute(self, attribute):
        return attribute  # TODO

    def get_file_list(self, path):
        res = requests.get(self.commands_format % (self.host, "op=100&DIR=%s" % path))
        res = res.content.split()
        # print(res)
        if res[0] != b'WLANSD_FILELIST':
            raise FlashAirAPIError("Could not retrieve file list")

        files = []
        for i in range(1, len(res)):
            directory, fname, size, attribute, date, time = res[i].decode().split(',')
            datetime = self.format_datetime(date, time)
            attribute = self.format_attribute(attribute)
            files.append({
                "directory": directory,
                "filename": fname,
                "size": size,
                "attribute": attribute,
                "datetime": datetime,
            })
        return files

    def transfer_latest_pictures(self, count=1, tmpdir=None):
        dir_list = self.get_file_list('/DCIM')
        files = []
        for x in dir_list:
            if x['filename'] != '100__TSB':  # Ignore file from SD card
                files.extend(self.get_file_list('/DCIM/' + x['filename']))

        files.sort(key=lambda x: x['filename'], reverse=True)  # TODO: sort by date
        images = []
        fnames = []
        for i in range(count):
            if i >= len(files):
                break
            path = '%s/%s' % (files[i]['directory'], files[i]['filename'])
            url = self.path_format % (self.host, path)
            print(url)
            new_image = imageio.imread(BytesIO(requests.get(url).content), format='jpg')
            if not (tmpdir):
                images.append(new_image)
            else:
                # print(files[i]['filename'])
                fname = os.path.join(tmpdir, files[i]['filename'])
                imageio.imwrite(fname, new_image)
                fnames.append(fname)

        if not (tmpdir):
            return images[::-1]
        else:
            return fnames

    def delete_all(self):
        files = []
        dir_list = self.get_file_list('/DCIM')
        for x in dir_list:
            if x['filename'] != '100__TSB':  # Ignore file from SD card
                files.extend(self.get_file_list('/DCIM/' + x['filename']))

        for f in files:
            requests.get(self.delete_format % (self.host, f['directory'] + '/' + f['filename']))

class Camera(hal.AbstractCamera):
    """
    Sony Remote Control API.

    Examples
    --------
    >>> import numpy as np
    >>> from romiscanner.sony import Camera
    >>> cam = Camera('192.168.122.1', '10000', postview=True, rotation=0)
    >>> img = cam.grab(0)
    >>> arr = img.channels['rgb'].data
    >>> arr.shape

    >>> cam = Camera('192.168.122.1', '10000', postview=True, rotation=270)
    >>> img = cam.grab(0)
    >>> arr = np.array(img.channels['rgb'].data)
    >>> arr.shape

    """

    def __init__(self, device_ip: str,
                 api_port: str,
                 timeout: Time_s = 10,
                 postview: bool = False,
                 use_adb: bool = False,
                 use_flashair: bool = False,
                 flashair_host: str = None,
                 camera_params: dict = None,
                 rotation: int = 0):

        self.sony_cam = SonyCamAPI(device_ip, api_port, timeout=timeout)
        self.postview = postview
        self.use_flashair = use_flashair
        self.use_adb = use_adb
        if use_flashair and use_adb:
            raise SonyCamError("Cannot use both flashair and adb for transfer")
        if use_flashair:
            if flashair_host is None:
                raise SonyCamError("Must provide flashair host IP")
            self.flashair = FlashAirAPI(flashair_host)

        self.camera_params = camera_params
        self.rotation = rotation  # degrees counter-clockwise
        self.start()

    def start(self):
        self.sony_cam.start_shoot_mode()
        self.sony_cam.set_shoot_mode("still")
        if self.camera_params is not None:
            self.sony_cam.setup_camera(self.camera_params)

    def channels(self):
        return ['rgb']

    def grab(self, idx: int, metadata: dict = None) -> DataItem:
        data_item = DataItem(idx, metadata)
        res = self.sony_cam.take_picture()
        url = res[0]
        if self.postview:  # Download image from postview
            data = imageio.imread(BytesIO(requests.get(url).content))
        elif self.use_adb:  # Download using android debug
            images = self.sony_cam.adb_transfer_pictures(count=1)
            data = images[0]
        elif self.use_flashair:  # Download on wifi sd card
            images = self.flashair.transfer_latest_pictures(count=1)
            data = images[0]
        else:  # Download using file transfer mode (not available on all cameras)
            self.sony_cam.start_transfer_mode()
            uri = self.sony_cam.get_source_list()[0]['source']
            content_list = self.sony_cam.get_content_list(count=1, uri=uri)
            content = content_list[0]
            content = content['content']['original'][0]
            url = content['url']
            data = imageio.imread(BytesIO(requests.get(url).content))
            self.sony_cam.start_shoot_mode()

        if self.rotation != 0:
            data = Image.fromarray(data)
            data = data.rotate(self.rotation)

        data_item.add_channel('rgb', data)
        return data_item
