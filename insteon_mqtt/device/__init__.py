#===========================================================================
#
# Insteon device classes
#
#===========================================================================
# flake8: noqa

__doc__ = """Insteon device classes.

Devices are physical entities in the Insteon system.  They can be
commanded via MQTT and are responsible for responding to messages
received over the network with their address.

Each device stores a scene (all link) database that matches the
database stored on the physical device.  This insures that when a
scene is activated, the device can notify every other device in the
scene to update to insure that the state of each device is consistent
with the state of the physical device.  This device is stored locally
on disk and must be manually refreshed if you change the pairings of
the devices with physical buttons.

Each device has a pair() method that can be used to correctly link it
to the PLM modem.  Devices must be paired as responders to the modem
first (hold the modem set button, then the device.
"""

#===========================================================================

from .Base import Base
from .BatterySensor import BatterySensor
from .Dimmer import Dimmer
from .FanLinc import FanLinc
from .IOLinc import IOLinc
from .KeypadLinc import KeypadLinc
from .Leak import Leak
from .MsgHistory import MsgHistory
from .Motion import Motion
from .Outlet import Outlet
from .Remote import Remote
from .SmokeBridge import SmokeBridge
from .Switch import Switch
from .Thermostat import Thermostat
