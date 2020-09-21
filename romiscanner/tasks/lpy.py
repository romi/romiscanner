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
import subprocess
import tempfile

import luigi
from romidata import RomiTask
from romiscanner.lpy import LpyFileset
from romiscanner.configs.lpy import VirtualPlantConfig


class VirtualPlant(RomiTask):
    upstream_task = LpyFileset
    lpy_file_id = luigi.Parameter()
    metadata = luigi.ListParameter(default=["angles", "internodes"])
    lpy_globals = luigi.DictParameter(default=
        { "SEED" : random.randint(0, 100000)}) #by default randomize lpy seed

    def run(self):
        from openalea import lpy
        from openalea.plantgl import all

        lpy_globals = json.loads(luigi.DictParameter().serialize(self.lpy_globals))

        with tempfile.TemporaryDirectory() as tmpdir:
            x = self.input().get().get_file(self.lpy_file_id)
            tmp_filename = os.path.join(tmpdir, "f.lpy")
            with open(tmp_filename, "wb") as f:
                f.write(x.read_raw())

            lsystem = lpy.Lsystem(tmp_filename, globals=lpy_globals)
            # lsystem.context().globals()["SEED"] = self.seed
            for lstring in lsystem:
                t = all.PglTurtle()
                lsystem.turtle_interpretation(lstring, t)
            scene = t.getScene()

            output_file = self.output_file()
            fname = os.path.join(tmpdir, "plant.obj")
            scene.save(fname)
            classes = luigi.DictParameter().serialize(VirtualPlantConfig().classes).replace(" ", "")
            subprocess.run(["romi_split_by_material", "--", "--classes", classes, fname, fname], check=True)
            subprocess.run(["romi_clean_mesh", "--", fname, fname], check=True)
            output_file.import_file(fname)

            output_mtl_file = self.output().get().create_file(output_file.id + "_mtl")
            output_mtl_file.import_file(fname.replace("obj", "mtl"))

        for m in self.metadata:
            m_val = lsystem.context().globals()[m]
            output_file.set_metadata(m, m_val)