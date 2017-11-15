#===========================================================================
#
# Insteon-MQTT bridge Python package
#
#===========================================================================

__doc__ = """TODO: doc"""

#===========================================================================
import functools
from . import device

# Possible devices we can read and build from the config file.
devices = {
    'dimmer' : device.Dimmer,
    'motion' : device.Motion,
    'on_off' : device.OnOff,
    'smoke_bridge' : device.SmokeBridge,
    'mini_remote8' : functools.partial(device.Remote, num=8),
    }

#===========================================================================
def find(name):
    name = name.lower()
    dev = devices.get(name, None)
    if not dev:
        raise Exception("Unknown device name '%s'" % name)

    return dev

#===========================================================================
