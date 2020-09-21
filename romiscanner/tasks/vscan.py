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

import json
import os
import random

import luigi
from romidata import io
from romiscanner.configs.lpy import VirtualPlantConfig
from romiscanner.log import logger
from romiscanner.scan import HdriFileset, SceneFileset, PaletteFileset
from romiscanner.tasks.lpy import VirtualPlant
from romiscanner.tasks.scan import Scan
from romiscanner.vscan import VirtualScanner


class VirtualScan(Scan):
    """ A task for running a virtual scan with Blender.

    Module: romiscan.tasks.vscan
    Default upstream tasks: None

    Parameters
    ----------
    load_scene : bool
        If `True` load a scene file in Blender.
    scene_file_id : str
        Name of scene file to load, required if `load_scene` is `True`.
    use_palette : bool
        If `True` use the "palette" fileset.
    use_hdri : bool
        If `True` use a "HDRi" fileset.
    obj_fileset : {VirtualPlant, ObjFileset}
        If "ObjFileset", indicate where to find the "obj" file.
        If "VirtualPlant", indicate ???.
        Default is `VirtualPlant`.
    hdri_fileset : HdriFileset
        Indicate where to find the "hdri" files.
    scene_fileset : SceneFileset
        Indicate where to find the "scene" files.
    palette_fileset : PaletteFileset
        Indicate where to find the "palette" files.
    render_ground_truth : bool
        If `True`, export ground truth labelled Masks to be used with an evaluation task.

    See Also
    --------
    romiscanner.scan.ObjFileset
    romiscanner.scan.HdriFileset
    romiscanner.scan.LpyFileset
    romiscanner.scan.PaletteFileset
    romiscanner.tasks.scan.Scan
    romiscanner.tasks.vscan.VirtualScanner

    """
    load_scene = luigi.BoolParameter(default=False)
    scene_file_id = luigi.Parameter(default="")

    use_palette = luigi.BoolParameter(default=False)
    use_hdri = luigi.BoolParameter(default=False)

    obj_fileset = luigi.TaskParameter(default=VirtualPlant)
    hdri_fileset = luigi.TaskParameter(default=HdriFileset)
    scene_fileset = luigi.TaskParameter(default=SceneFileset)
    palette_fileset = luigi.TaskParameter(default=PaletteFileset)

    render_ground_truth = luigi.BoolParameter(default=False)

    def requires(self):
        requires = {
            "object": self.obj_fileset()
        }
        if self.use_hdri:
            requires["hdri"] = self.hdri_fileset()
        if self.use_palette:
            requires["palette"] = self.palette_fileset()
        if self.load_scene:
            requires["scene"] = self.scene_fileset()
        return requires

    def load_scanner(self):
        # Load the scanner configuration (create in Scan class)
        scanner_config = json.loads(luigi.DictParameter().serialize(self.scanner))
        #
        obj_fileset = self.input()["object"].get()
        if self.load_scene:
            scene_fileset = self.input()["scene"].get()
            for f in scene_fileset.get_files():
                logger.debug(f.id)
            self.tmpdir = io.tmpdir_from_fileset(scene_fileset)
            scanner_config["scene"] = os.path.join(self.tmpdir.name,
                                                   scene_fileset.get_file(
                                                       self.scene_file_id).filename)

        if self.render_ground_truth:
            scanner_config["classes"] = list(
                VirtualPlantConfig().classes.values())

        vscan = VirtualScanner(**scanner_config)
        while True:
            obj_file = random.choice(obj_fileset.get_files())
            if "obj" in obj_file.filename:
                break
        mtl_file = obj_fileset.get_file(obj_file.id + "_mtl")
        palette_file = None
        if self.use_palette:
            palette_file = random.choice(
                self.input()["palette"].get().get_files())
        vscan.load_object(obj_file, mtl=mtl_file, palette=palette_file)

        if self.use_hdri:
            hdri_fileset = self.input()["hdri"].get()
            hdri_file = random.choice(hdri_fileset.get_files())
            vscan.load_background(hdri_file)

        bb = vscan.get_bounding_box()
        self.output().get().set_metadata("bounding_box", bb)
        return vscan