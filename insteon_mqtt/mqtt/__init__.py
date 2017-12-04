#===========================================================================
#
# MQTT handlers classes
#
#===========================================================================

__doc__ = """TODO: doc
"""

#===========================================================================

from .Mqtt import Mqtt
#from .Dimmer import Dimmer
#from .Motion import Motion
#from .Remote import Remote
#from .SmokeBridge import SmokeBridge
from .Switch import Switch
from . import util

# Map Insteon device class to MQTT device class.
from .. import device as IDev
device_map = {
    #IDev.Dimmer : Dimmer,
    #IDev.Motion : Motion,
    #IDev.Remote : Remote,
    #IDev.SmokeBridge : SmokeBridge,
    IDev.Switch : Switch,
    }
del IDev
