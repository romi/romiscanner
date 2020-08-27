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
import atexit
import time

import serial
from romiscanner import hal

from .log import logger

GRBL_SETTINGS = {
    "$0": ("Step pulse", "microseconds"),
    "$1": ("Step idle delay", "milliseconds"),
    "$2": ("Step port invert", "mask"),
    "$3": ("Direction port invert", "mask"),
    "$4": ("Step enable invert", "boolean"),
    "$5": ("Limit pins invert", "boolean"),
    "$6": ("Probe pin invert", "boolean"),
    "$10": ("Status report", "mask"),
    "$11": ("Junction deviation", "mm"),
    "$12": ("Arc tolerance", "mm"),
    "$13": ("Report inches", "boolean"),
    "$20": ("Soft limits", "boolean"),
    "$21": ("Hard limits", "boolean"),
    "$22": ("Homing cycle", "boolean"),
    "$23": ("Homing dir invert", "mask"),
    "$24": ("Homing feed", "mm/min"),
    "$25": ("Homing seek", "mm/min"),
    "$26": ("Homing debounce", "milliseconds"),
    "$27": ("Homing pull-off", "mm"),
    "$30": ("Max spindle speed", "RPM"),
    "$31": ("Min spindle speed", "RPM"),
    "$32": ("Laser mode", "boolean"),
    "$100": ("X steps/mm", "steps/mm"),
    "$101": ("Y steps/mm", "steps/mm"),
    "$102": ("Z steps/mm", "steps/mm"),
    "$110": ("X Max rate", "mm/min"),
    "$111": ("Y Max rate", "mm/min"),
    "$112": ("Z Max rate", "mm/min"),
    "$120": ("X Acceleration", "mm/sec^2"),
    "$121": ("Y Acceleration", "mm/sec^2"),
    "$122": ("Z Acceleration", "mm/sec^2"),
    "$130": ("X Max travel", "mm"),
    "$131": ("Y Max travel", "mm"),
    "$132": ("Z Max travel", "mm")
}


class CNC(hal.AbstractCNC):
    """CNC functionalities.

    Attributes
    ----------
    port : str
        Serial port to use for communication with the CNC.
    baud_rate : int
        Communication baudrate, should be 115200 for the Arduino UNO.
    homing : bool
        If `True`, axes homing will be performed upon CNC object instantiation [RECOMMENDED].
    x_lims : (int, int)
        The allowed range of X-axis positions.
    y_lims : (int, int)
        The allowed range of Y-axis positions.
    z_lims : (int, int)
        The allowed range of Z-axis positions.
    serial_port : serial.Serial
        The `Serial` instance used to send commands to the grbl.
    x : int
        The position of the CNC arm along the X-axis.
    y : int
        The position of the CNC arm along the Y-axis.
    z : int
        The position of the CNC arm along the Z-axis.

    References
    ----------
    http://linuxcnc.org/docs/html/gcode/g-code.html

    """

    def __init__(self, port="/dev/ttyUSB0", baud_rate=115200, homing=True,
                 x_lims=None, y_lims=None, z_lims=None):
        """Constructor.

        Parameters
        ----------
        port : str, optional
            Serial port to use for communication with the CNC, `"/dev/ttyUSB0"` by default.
        baud_rate : int, optional
            Communication baudrate, `115200` by default (should work for the Arduino UNO).
        homing : bool, optional
            If `True` (default), axes homing will be performed upon CNC object instantiation [RECOMMENDED].
        x_lims : (int, int), optional
            The allowed range of X-axis positions, if `None` (default) use the settings from grbl ("$130", see GRBL_SETTINGS).
        y_lims : (int, int), optional
            The allowed range of Y-axis positions, if `None` (default) use the settings from grbl ("$131", see GRBL_SETTINGS).
        z_lims : (int, int), optional
            The allowed range of Z-axis positions, if `None` (default) use the settings from grbl ("$132", see GRBL_SETTINGS).

        Examples
        --------
        >>> from romiscanner.grbl import CNC
        >>> cnc = CNC("/dev/ttyACM0")
        >>> cnc.moveto(200, 200, 50)
        >>> cnc.moveto_async(200, 200, 50)
        >>> cnc.send_cmd("$$")
        >>> cnc.print_grbl_settings()

        """
        self.port = port
        self.baud_rate = baud_rate
        self.homing = homing
        self.x_lims = x_lims
        self.y_lims = y_lims
        self.z_lims = z_lims
        self.serial_port = None
        self.x = 0
        self.y = 0
        self.z = 0
        self.grbl_settings = None
        self._start()
        atexit.register(self.stop)

    def _check_axes_limits(self, axe_limits, grbl_limits, axes):
        try:
            assert axe_limits[0] >= grbl_limits[0] and axe_limits[1] <= grbl_limits[1]
        except AssertionError:
            msg = f"Given {axes}-axis limits are WRONG!\n"
            msg += f"Should be in '{grbl_limits[0]}:{grbl_limits[1]}', but got '{axe_limits[0]}:{axe_limits[1]}'!"
            raise ValueError(msg)

    def _start(self):
        """ Start the serial connection with the Arduino & initialize the CNC (hardware).

        References
        ----------
        http://linuxcnc.org/docs/html/gcode/g-code.html#gcode:g90-g91
        http://linuxcnc.org/docs/html/gcode/g-code.html#gcode:g20-g21

        """
        self.serial_port = serial.Serial(self.port, self.baud_rate, timeout=10)
        self.has_started = True
        self.serial_port.write("\r\n\r\n".encode())
        time.sleep(2)
        self.serial_port.flushInput()
        # Performs axes homing if required:
        if self.homing:
            self.home()
        # Set to "absolute distance mode":
        self.send_cmd("g90")
        # Use millimeters for length units:
        self.send_cmd("g21")

        # Initialize axes limits with grbl settings if not set, else check given settings:
        self.grbl_settings = self.get_grbl_settings()
        if self.x_lims is None:
            self.x_lims = self.grbl_settings["$130"]
        else:
            self._check_axes_limits(self.x_lims, [0, self.grbl_settings["$130"]], 'X')
        if self.y_lims is None:
            self.y_lims = self.grbl_settings["$131"]
        else:
            self._check_axes_limits(self.y_lims, [0, self.grbl_settings["$131"]], 'Y')
        if self.z_lims is None:
            self.z_lims = self.grbl_settings["$132"]
        else:
            self._check_axes_limits(self.z_lims, [0, self.grbl_settings["$132"]], 'Z')

    def stop(self):
        """ Close the serial connection."""
        if (self.has_started):
            self.serial_port.close()

    def get_position(self):
        """ Returns the xyz position of the CNC."""
        return self.x, self.y, self.z

    def async_enabled(self):
        return True

    def home(self):
        """ Performs axes homing procedure.

        References
        ----------
        https://github.com/gnea/grbl/wiki/Grbl-v1.1-Commands#h---run-homing-cycle
        http://linuxcnc.org/docs/html/gcode/g-code.html#gcode:g92

        """
        # Send grbl homming command:
        self.send_cmd("$H")
        # self.send_cmd("g28") #reaching workspace origin
        # Set current position to [0, 0, 0] (origin)
        # Note that there is a 'homing pull-off' value ($27)!
        self.send_cmd("g92 x0 y0 z0")

    def _check_move(self, x, y, z):
        """ Make sure the `moveto` coordinates are within the axes limits."""
        try:
            assert self.x_lims[0] < x < self.x_lims[1]
        except AssertionError:
            raise ValueError("Move command coordinates is outside the x-limits!")
        try:
            assert self.y_lims[0] < y < self.y_lims[1]
        except AssertionError:
            raise ValueError("Move command coordinates is outside the y-limits!")
        try:
            assert self.z_lims[0] < z < self.z_lims[1]
        except AssertionError:
            raise ValueError("Move command coordinates is outside the z-limits!")

    def moveto(self, x, y, z):
        """ Send a move command and wait until reaching target position.

        Parameters
        ----------
        x : int
            The position of the CNC arm along the X-axis.
        y : int
            The position of the CNC arm along the Y-axis.
        z : int
            The position of the CNC arm along the Z-axis.

        """
        self._check_move(x, y, z)
        self.moveto_async(x, y, z)
        self.wait()

    def moveto_async(self, x, y, z):
        """ Send a 'G0' move command.

        Parameters
        ----------
        x : int
            The position of the CNC arm along the X-axis.
        y : int
            The position of the CNC arm along the Y-axis.
        z : int
            The position of the CNC arm along the Z-axis.

        References
        ----------
        http://linuxcnc.org/docs/html/gcode/g-code.html#gcode:g0

        """
        self.send_cmd("g0 x%s y%s z%s" % (int(x), int(y), int(z)))
        self.x = int(x)
        self.y = int(y)
        self.z = int(z)
        time.sleep(0.1)  # Add a little sleep between calls

    def wait(self):
        """ Send a 1 second wait command to grbl.

        References
        ----------
        http://linuxcnc.org/docs/html/gcode/g-code.html#gcode:g4

        """
        self.send_cmd("g4 p1")

    def send_cmd(self, cmd):
        """ Send given command to grbl.

        Parameters
        ----------
        cmd : str
            A grbl compatible command.

        References
        ----------
        https://github.com/gnea/grbl/wiki/Grbl-v1.1-Commands

        """
        self.serial_port.reset_input_buffer()
        logger.debug("%s -> cnc" % cmd)
        self.serial_port.write((cmd + "\n").encode())
        grbl_out = self.serial_port.readlines()
        for out in grbl_out:
            logger.debug("cnc -> %s" % out.strip())
        time.sleep(0.1)
        return grbl_out

    def get_status(self):
        """ Returns grbl status."""
        self.serial_port.write("?".encode("utf-8"))
        try:
            res = self.serial_port.readline()
            res = res.decode("utf-8")
            res = res[1:-1]
            res = res.split('|')
            print(res)
            res_fmt = {}
            res_fmt['status'] = res[0]
            pos = res[1].split(':')[-1].split(',')
            pos = [-float(p) for p in pos]  # why - ?
            res_fmt['position'] = pos
        except:
            return None
        return res_fmt

    def get_grbl_settings(self):
        """ Returns the grbl settings as a dictionary {'param': value}."""
        str_settings = self.send_cmd("$$")
        settings = {}
        for line in str_settings:
            line = line.strip()  # remove potential leading and trailing whitespace & eol
            line = line.decode()
            if not line.startswith('$'):
                # All params are prefixed with a dollar sign '$'
                continue
            param, value = line.split("=")
            try:
                settings[param] = int(value)
            except ValueError:
                settings[param] = float(value)
        return settings

    def print_grbl_settings(self):
        """ Print the grbl settings.

        See Also
        --------
        GRBL_SETTINGS

        References
        ----------
        https://github.com/gnea/grbl/wiki/Grbl-v1.1-Configuration#grbl-settings

        """
        settings = self.get_grbl_settings()
        print("Obtained grbl settings:")
        for param, value in settings.items():
            param_name, param_unit = GRBL_SETTINGS[param]
            if param_unit in ['boolean', 'mask']:
                param_unit = f"({param_unit})"
            print(f" - ({param}) {param_name}: {value} {param_unit}")
