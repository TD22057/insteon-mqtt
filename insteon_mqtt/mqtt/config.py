#===========================================================================
#
# Configuration file utiltiies.
#
#===========================================================================

__doc__ = """Configuration file utilties
"""

#===========================================================================
from .. import device
from .Dimmer import Dimmer
from .FanLinc import FanLinc
from .Motion import Motion
from .Remote import Remote
from .SmokeBridge import SmokeBridge
from .Switch import Switch

devices = {
    device.Dimmer : Dimmer,
    device.FanLinc : FanLinc,
    device.Motion : Motion,
    device.Remote : Remote,
    device.SmokeBridge : SmokeBridge,
    device.Switch : Switch,
    }


#===========================================================================
def find(insteon_device):
    """Find a device class from a description.

    TODO: doc
    Valid inputs are defined in the config.devices dictionary.

    Args:
      name:   (str) The device type name.

    Returns:
      Returns the device class to use for the input.
    """
    cls = insteon_device.__class__

    return devices.get(cls, None)

#===========================================================================
