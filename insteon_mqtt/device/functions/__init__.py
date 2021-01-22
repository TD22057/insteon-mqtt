#===========================================================================
#
# Insteon device function classes
#
#===========================================================================
# flake8: noqa

__doc__ = """Insteon device function classes.

These are all abstract classes that cover distinct functionality that is
present on more than one device type, but not present on all device types

Each class should be distinct to a series of closely related functionality.
The idea is that new Insteon devices can be quickly added by selecting from
the list of available functions to inherit from.
"""

#===========================================================================

from .Scene import Scene
from .Backlight import Backlight
from .ManualCtrl import ManualCtrl
