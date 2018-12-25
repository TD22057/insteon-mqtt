#===========================================================================
#
# Configuration file utiltiies.
#
#===========================================================================

__doc__ = """Configuration file utilties

Mainly used to map insteon classes to the corresponding MQTT class to use
with it.
"""

#===========================================================================
from .. import device
from ..Modem import Modem
from .BatterySensor import BatterySensor
from .Dimmer import Dimmer
from .FanLinc import FanLinc
from .IOLinc import IOLinc
from .KeypadLinc import KeypadLinc
from .Leak import Leak
from .Modem import Modem as MqttModem
from .Motion import Motion
from .Outlet import Outlet
from .Remote import Remote
from .SmokeBridge import SmokeBridge
from .Switch import Switch
from .Thermostat import Thermostat

# Map Insteon device classes to MQTT classes.
devices = {
    Modem : MqttModem,
    device.BatterySensor : BatterySensor,
    device.Dimmer : Dimmer,
    device.FanLinc : FanLinc,
    device.IOLinc : IOLinc,
    device.KeypadLinc : KeypadLinc,
    device.Leak : Leak,
    device.Motion : Motion,
    device.Outlet : Outlet,
    device.Remote : Remote,
    device.SmokeBridge : SmokeBridge,
    device.Switch : Switch,
    device.Thermostat : Thermostat,
    }


#===========================================================================
def find(insteon_device):
    """Find an MQTT class to use for the input insteon device object.

    Args:
      insteon_device:  The insteon device object.

    Returns:
      Returns the MQTT class to use for the input.
    """
    cls = insteon_device.__class__

    return devices.get(cls, None)

#===========================================================================
