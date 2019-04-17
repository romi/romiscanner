# -*- python -*-
# -*- coding: utf-8 -*-
#
#       File author(s):
#           Jonathan Legrand <jonathan.legrand@ens-lyon.fr>
#
#       File contributor(s):
#           Peter Hanappe <peter@hanappe.com>
#           Jonathan Legrand <jonathan.legrand@ens-lyon.fr>
#
#       File maintainer(s):
#           Peter Hanappe <peter@hanappe.com>
#
#       Distributed under XXXXX license.
#
# ------------------------------------------------------------------------------


"""
OMERO CLI (Command Line Interface) implementation for the database module in
the ROMI project.

Notes
-----
Zeroc-Ice install for Python3 in conda env:
``conda install -c bioconda zeroc-ice=3.6.3=py35_0``

The CLI is currently bundled:
  * with the OMERO.server including all functionalities of the CLI
  * with the OMERO.python including all functionalities of the CLI except for the import functionality

Matching version of OMERO server & Zeroc-Ice installed:
OMERO.server-5.4.9-ice36-b101
https://downloads.openmicroscopy.org/omero/5.4.9/artifacts/OMERO.server-5.4.9-ice36-b101.zip

OMERO.py-5.4.9-ice36-b101
https://downloads.openmicroscopy.org/omero/5.4.9/artifacts/OMERO.py-5.4.9-ice36-b101.zip


Get the server version:
``$ wget https://downloads.openmicroscopy.org/omero/5.4.9/artifacts/OMERO.server-5.4.9-ice36-b101.zip``
Unzip it:
``$ unzip OMERO.server-5.4.9-ice36-b101.zip``

Python3 conversion:

1. Apply ``2to3`` transformation script to python scripts (directly write changes, no backups):
``$ 2to3 OMERO.server-5.4.9-ice36-b101/ --write --nobackups``

2. Performs following replacements:
  * 'threading._Event' -> 'threading.Event'
  * 'threading._Timer' -> 'threading.Timer'
  * 'from types import X' -> '', with X in following replacements:
    * 'IntType' -> 'int'
    * 'LongType' -> 'int'
    * 'ListType' -> 'list'
    * 'TupleType' -> 'tuple'
    * 'StringType' -> 'str'
    * 'StringTypes' -> 'str'
    * 'UnicodeType' -> 'str'
    * 'BooleanType' -> 'bool'

3. Add OMERO to ``$PYTHONPATH`` environment variable, by adding these lines to:
  * to ``miniconda*/bin/activate`` if in a conda env:
  .. code_block::
     if [[ "$@" == "lettucethink" ]]; then
         export OMERO_PREFIX=~/Projects/ROMI/OMERO.server-5.4.9-ice36-b101
         export PYTHONPATH=$PYTHONPATH:$OMERO_PREFIX/lib/python
     fi

  * to ``~/.bashrc``:
  .. code_block::
     export OMERO_PREFIX=~/Projects/ROMI/OMERO.server-5.4.9-ice36-b101
     export PYTHONPATH=$PYTHONPATH:$OMERO_PREFIX/lib/python

"""

import copy
import json
import os
import sys
from shutil import copyfile

from lettucethink import error
from lettucethink.db import db_api as db

from omero.gateway import BlitzGateway

HOST = 'db.romi-project.eu'
USERNAME = 'jonathan'
PORT = 4064

CONN_ATTRS = ['host', 'username', 'pwd', 'port']


class DB(db.DB):

    def __init__(self, host=HOST, username=USERNAME, pwd=None, port=PORT):
        """Database constructor.

        Uses host URL, user name, associated password and port to connect to
        database.

        Parameters
        ----------
        host : str
            OMERO server to connect to
        username : str
            user name to use to connect to OMERO server
        pwd : str
            password associated to OMERO server
        port : int
            port number to use to communicate with the OMERO.server

        Examples
        --------
        >>> from lettucethink.db.ome_cli_db import DB
        >>> omeromi = DB()
        >>> omeromi.connect(pwd='B@D5%5b4dT&#he3f')

        """
        # Defines hidden attributes:
        self._connected = False  # database connexion status, not connected by default

        # Defines attributes:
        self.host = host
        self.username = username
        self.pwd = pwd  # Is it OK to save password ?
        self.port = port

        attr_vals = [getattr(self, attr, None) for attr in CONN_ATTRS]
        if None not in attr_vals:
            self.connect(host=self.host, username=self.username, pwd=self.pwd,
                         port=self.port)

        # self.scans = _load_scans(self)

    def _is_connected(self):
        """Test if connected to the OMERO database. """
        if not self._connected:
            msg = "Error: Connection not available to {}:{}!"
            msg += "Please check your user name () and password.\n"
            raise ValueError(msg.format(self.host, self.port, self.username))
        else:
            return self._connected

    def connect(self, **kwargs):
        """Connect to the OMERO database.

        Provides keyword arguments not provided to DB instance at creation.

        Other Parameters
        ----------------
        host : str
            OMERO server to connect to
        username : str
            user name to use to connect to OMERO server
        pwd : str
            password associated to OMERO server
        port : int
            port number to use to communicate with the OMERO.server

        Returns
        -------
        bool
            connexion status, True if connected

        Raises
        ------
        ValueError
            if could not connect to database with given
        """

        for attr in CONN_ATTRS:
            kwd = kwargs.get(attr, None)
            if kwd is not None:
                setattr(self, attr, kwd)

        self._connexion = BlitzGateway(self.username, self.pwd, host=self.host,
                                       port=self.port)
        self._connected = self._connexion.connect()
        return self._is_connected()

    def disconnect(self):
        """Disconnect from OMERO database. """
        try:
            self._connexion.close()
        except:
            raise IOError("Not connected yet!")

    def get_scans(self):
        return self.scans

    def get_scan(self, id):
        for scan in self.scans:
            if scan.get_id() == id:
                return scan
        return None

    def create_scan(self, id):
        if not _is_valid_id(id):
            raise error.Error("Invalid id")
        if self.get_scan(id) != None:
            raise error.Error("Duplicate scan name: %s" % id)
        scan = Scan(self, id)
        _make_scan(scan)
        self.scans.append(scan)
        return scan


class Scan(db.Scan):

    def __init__(self, db, id):
        super().__init__(db, id)
        self.metadata = None
        self.filesets = []

    def get_filesets(self):
        return self.filesets  # Copy?

    def get_fileset(self, id):
        for fileset in self.filesets:
            if fileset.get_id() == id:
                return fileset
        return None

    def get_metadata(self, key=None):
        return _get_metadata(self.metadata, key)

    def set_metadata(self, data, value=None):
        if self.metadata == None:
            self.metadata = {}
        _set_metadata(self.metadata, data, value)
        _store_scan_metadata(self)

    def create_fileset(self, id):
        if not _is_valid_id(id):
            raise error.Error("Invalid id")
        if self.get_fileset(id) != None:
            raise error.Error("Duplicate fileset name: %s" % id)
        fileset = Fileset(scan.db, self, id)
        _make_fileset(fileset)
        self.filesets.append(fileset)
        self.store()
        return fileset

    def store(self):
        _store_scan(self)


class Fileset(db.Fileset):

    def __init__(self, db, scan, id):
        super().__init__(db, scan, id)
        self.metadata = None
        self.files = []

    def get_files(self):
        return self.files

    def get_metadata(self, key):
        return _get_metadata(self.metadata, key)

    def set_metadata(self, data, value=None):
        if self.metadata == None:
            self.metadata = {}
        _set_metadata(self.metadata, data, value)
        _store_fileset_metadata(self)

    def create_file(self, id):
        file = File(self.db, self, id, None)
        self.files.append(file)
        self.store()
        return file

    def store(self):
        self.scan.store()


class File(db.File):

    def __init__(self, db, fileset, id, filename):
        super().__init__(db, fileset, id)
        self.filename = filename
        self.metadata = None

    def get_metadata(self, key):
        return _get_metadata(self.metadata, key)

    def set_metadata(self, data, value=None):
        if self.metadata == None:
            self.metadata = {}
        _set_metadata(self.metadata, data, value)
        _store_file_metadata(self)

    def write_image(self, type, image):
        filename = _get_filename(self, type)
        path = _file_path(self, filename)
        imageio.imwrite(path, image)
        self.filename = filename
        self.store()

    def write_text(self, type, string):
        filename = _get_filename(self, type)
        path = _file_path(self, filename)
        with open(path, "w") as f:
            f.write(string)
        self.filename = filename
        self.store()

    def write_bytes(self, type, buffer):
        filename = _get_filename(self, type)
        path = _file_path(self, filename)
        with open(path, "wb") as f:
            f.write(buffer)
        self.filename = filename
        self.store()

    def import_file(self, path):
        filename = os.path.basename(path)
        newpath = _file_path(self, filename)
        copyfile(path, newpath)
        self.filename = filename
        self.store()

    def read_image(self):
        path = _file_path(self, self.filename)
        return imageio.imread(path)

    def read_text(self):
        path = _file_path(self, self.filename)
        with open(path, "r") as f:
            return f.read()

    def read_bytes(self):
        path = _file_path(self, self.filename)
        with open(path, "rb") as f:
            return f.read()

    def store(self):
        self.fileset.store()


##################################################################
#
# the ugly stuff...
#

# load the database

def _load_scans(db):
    scans = []
    names = os.listdir(db.basedir)
    for name in names:
        scan = Scan(db, name)
        if (os.path.isdir(_scan_path(scan))
                and os.path.isfile(_scan_files_json(scan))):
            scan.filesets = _load_scan_filesets(scan)
            scan.metadata = _load_scan_metadata(scan)
            scans.append(scan)
    return scans


def _load_scan_filesets(scan):
    filesets = []
    files_json = _scan_files_json(scan)
    with open(files_json, "r") as f:
        structure = json.load(f)
    filesets_info = structure["filesets"]
    if isinstance(filesets_info, list):
        for fileset_info in filesets_info:
            fileset = _load_fileset(scan, fileset_info)
            filesets.append(fileset)
    else:
        raise error.Error("%s: filesets is not a list" % files_json)
    return filesets


def _load_fileset(scan, fileset_info):
    fileset = _parse_fileset(scan.db, scan, fileset_info)
    fileset.files = _load_fileset_files(fileset, fileset_info)
    fileset.metadata = _load_fileset_metadata(fileset)
    return fileset


def _parse_fileset(db, scan, fileset_info):
    id = fileset_info.get("id")
    if id == None:
        raise error.Error("Fileset: No ID")
    fileset = Fileset(db, scan, id)
    path = _fileset_path(fileset)
    if not os.path.isdir(path):
        raise error.Error(
            "Fileset: Fileset directory doesn't exists: %s" % path)
    return fileset


def _load_fileset_files(fileset, fileset_info):
    files = []
    files_info = fileset_info.get("files", [])
    if isinstance(files_info, list):
        for file_info in files_info:
            file = _load_file(fileset, file_info)
            files.append(file)
    else:
        raise error.Error("files.json: expected a list for files")
    return files


def _load_file(fileset, file_info):
    file = _parse_file(fileset, file_info)
    file.metadata = _load_file_metadata(file)
    return file


def _parse_file(fileset, file_info):
    id = file_info.get("id")
    if id == None:
        raise error.Error("File: No ID")
    filename = file_info.get("file")
    if filename == None:
        raise error.Error("File: No filename")
    file = File(fileset.db, fileset, id, filename)
    path = _file_path(file, filename)
    if not os.path.isfile(path):
        raise error.Error("File: File doesn't exists: %s" % path)
    return file


# load/store metadata from disk

def _load_metadata(path):
    if os.path.isfile(path):
        with open(path, "r") as f:
            r = json.load(f)
        if not isinstance(r, dict):
            raise error.Error("Not a JSON object: %s" % path)
        return r
    else:
        return {}


def _load_scan_metadata(scan):
    return _load_metadata(_scan_metadata_path(scan))


def _load_fileset_metadata(fileset):
    return _load_metadata(_fileset_metadata_path(fileset))


def _load_file_metadata(file):
    return _load_metadata(_file_metadata_path(file))


def _mkdir_metadata(path):
    dir = os.path.dirname(path)
    if not os.path.isdir(dir):
        os.makedirs(dir)


def _store_metadata(path, metadata):
    _mkdir_metadata(path)
    with open(path, "w") as f:
        json.dump(metadata, f, sort_keys=True,
                  indent=4, separators=(',', ': '))


def _store_scan_metadata(scan):
    _store_metadata(_scan_metadata_path(scan),
                    scan.metadata)


def _store_fileset_metadata(fileset):
    _store_metadata(_fileset_metadata_path(fileset),
                    fileset.metadata)


def _store_file_metadata(file):
    _store_metadata(_file_metadata_path(file),
                    file.metadata)


#

def _get_metadata(metadata, key):
    # Do a deepcopy of the return value because we don't want to
    # caller the inadvertedly change the values.
    if metadata == None:
        return {}
    elif key == None:
        return copy.deepcopy(metadata)
    else:
        return copy.deepcopy(metadata.get(str(key)))


def _set_metadata(metadata, data, value):
    if isinstance(data, str):
        if value == None:
            raise error.Error("No value given for key %s" % data)
        # Do a deepcopy of the value because we don't want to caller
        # the inadvertedly change the values.
        metadata[data] = copy.deepcopy(value)
    elif isinstance(data, dict):
        for key, value in data.items():
            _set_metadata(metadata, key, value)
    else:
        raise error.Error("Invalid key: ", data)


#

def _make_fileset(fileset):
    path = _fileset_path(fileset)
    if not os.path.isdir(path):
        os.makedirs(path)


def _make_scan(scan):
    path = _scan_path(scan)
    if not os.path.isdir(path):
        os.makedirs(path)


# paths

def _get_filename(file, type):
    return file.id + "." + type


def _scan_path(scan):
    return os.path.join(scan.db.basedir,
                        scan.id)


def _fileset_path(fileset):
    return os.path.join(fileset.db.basedir,
                        fileset.scan.id,
                        fileset.id)


def _file_path(file, filename):
    return os.path.join(file.db.basedir,
                        file.fileset.scan.id,
                        file.fileset.id,
                        filename)


def _scan_files_json(scan):
    return os.path.join(scan.db.basedir,
                        scan.id,
                        "files.json")


def _scan_metadata_path(scan):
    return os.path.join(scan.db.basedir,
                        scan.id,
                        "metadata",
                        "metadata.json")


def _fileset_metadata_path(fileset):
    return os.path.join(fileset.db.basedir,
                        fileset.scan.id,
                        "metadata",
                        fileset.id + ".json")


def _file_metadata_path(file):
    return os.path.join(file.db.basedir,
                        file.fileset.scan.id,
                        "metadata",
                        file.fileset.id,
                        file.id + ".json")


# store a scan to disk

def _file_to_dict(file):
    return {"id": file.get_id(), "file": file.filename}


def _fileset_to_dict(fileset):
    files = []
    for f in fileset.get_files():
        files.append(_file_to_dict(f))
    return {"id": fileset.get_id(), "files": files}


def _scan_to_dict(scan):
    filesets = []
    for fileset in scan.get_filesets():
        filesets.append(_fileset_to_dict(fileset))
    return {"filesets": filesets}


def _store_scan(scan):
    structure = _scan_to_dict(scan)
    files_json = _scan_files_json(scan)
    with open(files_json, "w") as f:
        json.dump(structure, f, sort_keys=True,
                  indent=4, separators=(',', ': '))


#

def _is_valid_id(id):
    return True  # haha  (FIXME!)
