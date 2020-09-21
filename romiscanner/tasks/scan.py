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

import importlib
import json

import luigi
from romidata import RomiTask, FilesetTarget, DatabaseConfig
from romiscanner.configs.scan import ScanPath
from romiscanner.scanner import Scanner


class Scan(RomiTask):
    """ A task for running a scan, real or virtual.

    Module: romiscan.tasks.scan
    Default upstream tasks: None

    Parameters
    ----------
    metadata : DictParameter
        metadata for the scan
    scanner : DictParameter
        scanner hardware configuration (TODO: see hardware documentation)
    path : DictParameter
        scanner path configuration (TODO: see hardware documentation)

    """
    upstream_task = None
    metadata = luigi.DictParameter(default={})
    scanner = luigi.DictParameter(default={})

    def requires(self):
        return []

    def output(self):
        """Output for a RomiTask is a FileSetTarget, the fileset ID being
        the task ID.
        """
        return FilesetTarget(DatabaseConfig().scan, "images")

    def get_path(self):
        path_module = importlib.import_module(ScanPath().module)
        path = getattr(path_module, ScanPath().class_name)(**ScanPath().kwargs)
        return path

    def load_scanner(self):
        scanner_config = self.scanner

        cnc_module = scanner_config["cnc"]["module"]
        cnc_kwargs = scanner_config["cnc"]["kwargs"]
        cnc_module = importlib.import_module(cnc_module)
        cnc = getattr(cnc_module, "CNC")(**cnc_kwargs)

        gimbal_module = scanner_config["gimbal"]["module"]
        gimbal_kwargs = scanner_config["gimbal"]["kwargs"]
        gimbal_module = importlib.import_module(gimbal_module)
        gimbal = getattr(gimbal_module, "Gimbal")(**gimbal_kwargs)

        camera_module = scanner_config["camera"]["module"]
        camera_kwargs = scanner_config["camera"]["kwargs"]
        camera_module = importlib.import_module(camera_module)
        camera = getattr(camera_module, "Camera")(**camera_kwargs)
        return Scanner(cnc, gimbal, camera)

    def run(self, path=None):
        if path is None:
            path = self.get_path()

        scanner = self.load_scanner()
        metadata = json.loads(luigi.DictParameter().serialize(self.metadata))

        output_fileset = self.output().get()
        scanner.scan(path, output_fileset)
        output_fileset.set_metadata(metadata)
        output_fileset.set_metadata("channels", scanner.channels())


class CalibrationScan(Scan):
    """ A task for running a scan, real or virtual, with a calibration path.

    Module: romiscan.tasks.scan
    Colmap poses for subsequent scans. (TODO: see calibration documentation)
    Default upstream tasks: None

    Parameters
    ----------
    metadata : DictParameter
        metadata for the scan
    scanner : DictParameter
        scanner hardware configuration (TODO: see hardware documentation)
    path : DictParameter
        scanner path configuration (TODO: see hardware documentation)
    n_line : int ?
        number of shots taken on the orthogonal calibration lines

    """
    n_points_line = luigi.IntParameter(default=5)

    def run(self):
        path = Scan().get_path()
        path_module = importlib.import_module(ScanPath().module)
        calibration_path = getattr(path_module, "CalibrationScan")(path, self.n_points_line)
        Scan().run(path=calibration_path)