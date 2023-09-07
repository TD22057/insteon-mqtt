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
    def group_cmd_on_off(self, entry, is_on):
        """Determine if device turns on or off for this Group Command

        For switches, the database entry holds the actual on/off state that
        is applied when the ON command is received.

        Args:
          entry (DeviceEntry):  The local db entry for this group command.
          is_on (bool): Whether the command was ON or OFF
        Returns:
          is_on (bool):  The actual is_on value based on DB entry
        """
        # For on command, get actual on/off state from the database entry
        if is_on:
            is_on = bool(entry.data[0])
        return is_on

    #-----------------------------------------------------------------------
    def link_data_to_pretty(self, is_controller, data):
        """Converts Link Data1-3 to Human Readable Attributes

        This takes a list of the data values 1-3 and returns a dict with
        the human readable attibutes as keys and the human readable values
        as values.

        Args:
          is_controller (bool): True if the device is the controller, false
                        if it's the responder.
          data (list[3]): List of three data values.

        Returns:
          list[3]:  list, containing a dict of the human readable values
        """
        ret = [{'data_1': data[0]}, {'data_2': data[1]}, {'data_3': data[2]}]
        if not is_controller:
            on = 1 if data[0] else 0
            ret = [{'on_off': on},
                   {'data_2': data[1]},
                   {'data_3': data[2]}]
        return ret

    #-----------------------------------------------------------------------
    def link_data_from_pretty(self, is_controller, data):
        """Converts Link Data1-3 from Human Readable Attributes

        This takes a dict of the human readable attributes as keys and their
        associated values and returns a list of the data1-3 values.

        Args:
          is_controller (bool): True if the device is the controller, false
                        if it's the responder.
          data (dict[3]): Dict of three data values.

        Returns:
          list[3]: List of Data1-3 values
        """
        data_1, data_2, data_3 = super().link_data_from_pretty(is_controller,
                                                               data)
        if not is_controller:
            if 'on_off' in data:
                data_1 = 0xFF if data['on_off'] else 0x00
        return [data_1, data_2, data_3]

    #-----------------------------------------------------------------------
