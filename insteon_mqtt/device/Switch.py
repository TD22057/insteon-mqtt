#===========================================================================
#
# Insteon on/off device
#
#===========================================================================
from .base import ResponderBase
from .functions import Scene, Backlight, ManualCtrl
from .. import log

LOG = log.get_logger()


#===========================================================================
class Switch(Scene, Backlight, ManualCtrl, ResponderBase):
    """Insteon on/off switch device.

    This class can be used to model any device that acts like a on/off switch
    including wall switches, lamp modules, and appliance modules.

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).
    """
    def __init__(self, protocol, modem, address, name=None, config_extra=None):
        """Constructor

        Args:
          protocol (Protocol):  The Protocol object used to communicate
                   with the Insteon network.  This is needed to allow the
                   device to send messages to the PLM modem.
          modem (Modem):  The Insteon modem used to find other devices.
          address (Address):  The address of the device.
          name (str):  Nice alias name to use for the device.
          config_extra (dict): Extra configuration settings
        """
        super().__init__(protocol, modem, address, name, config_extra)

        # Update the group map with the groups to be paired and the handler
        # for broadcast messages from this group
        self.group_map.update({0x01: self.handle_on_off})

    #-----------------------------------------------------------------------
