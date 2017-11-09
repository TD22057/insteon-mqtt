#===========================================================================
#
# Insteon-MQTT bridge Python package
#
#===========================================================================

__doc__ = """TODO: doc"""

#===========================================================================
import functools
from .Dimmer import Dimmer
from .OnOff import OnOff
from .Remote import Remote
from .SmokeBridge import SmokeBridge

devices = {
    'dimmer' : Dimmer,
    'on_off' : OnOff,
    'smoke_bridge' : SmokeBridge,
    'remote8' : functools.partial(Remote, num=8),
    }

#===========================================================================
def find(name):
    name = name.lower()
    dev = devices.get(name, None)
    if not dev:
        raise Exception("Unknown device name '%s'" % name)

    return dev

#===========================================================================
