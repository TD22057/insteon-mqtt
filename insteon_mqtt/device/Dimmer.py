#===========================================================================
#
# Dimmer device module.  Used for anything that acts like a dimmer
# including wall switches, lamp modules, and some remotes.
#
#===========================================================================
from .base import DimmerBase
from .functions import Scene, Backlight
from ..CommandSeq import CommandSeq
from .. import handler
from .. import log
from .. import message as Msg
from .. import on_off
from .. import util

LOG = log.get_logger()


class Dimmer(Scene, Backlight, DimmerBase):
    """Insteon dimmer device.

    This class can be used to model any device that acts like a dimmer
    including wall switches, lamp modules, and some remotes.

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).
    """
    def __init__(self, protocol, modem, address, name=None, config_extra=None):
        """Constructor

        Args:
          protocol (Protocol): The Protocol object used to communicate
                   with the Insteon network.  This is needed to allow the
                   device to send messages to the PLM modem.
          modem (Modem): The Insteon modem used to find other devices.
          address (Address): The address of the device.
          name (str): Nice alias name to use for the device
          config_extra (dict): Extra configuration settings
        """
        super().__init__(protocol, modem, address, name, config_extra)

        # Update the group map with the groups to be paired and the handler
        # for broadcast messages from this group
        self.group_map.update({0x01: self.handle_on_off})

    #-----------------------------------------------------------------------
    def cmd_on_values(self, mode, level, transition, group):
        """Calculate Cmd Values for On

        Args:
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          level (int): On level between 0-255.
          transition (int): Ramp rate for the transition in seconds.
        Returns
          cmd1, cmd2 (int): Value of cmds for this device.
        """
        if transition or mode == on_off.Mode.RAMP:
            LOG.error("Device %s does not support transition.", self.addr)
            mode = on_off.Mode.NORMAL if mode == on_off.Mode.RAMP else mode
        if level is None:
            # If level is not specified it uses the level that the device
            # would go to if the button was physically pressed.
            level = self.derive_on_level(mode)
        cmd1 = on_off.Mode.encode(True, mode)
        return (cmd1, level)

    #-----------------------------------------------------------------------
    def link_data(self, is_controller, group, data=None):
        """Create default device 3 byte link data.

        This is the 3 byte field (D1, D2, D3) stored in the device database
        entry.  This overrides the defaults specified in base.py for
        specific values used by dimming devices.

        For controllers, the default fields are:
           D1: number of retries (0x03)
           D2: unknown (0x00)
           D3: the group number on the local device (0x01)

        For responders, the default fields are:
           D1: on level for switches and dimmers (0xff)
           D2: ramp rate (0x1f, or .1s)
           D3: the group number on the local device (0x01)

        Args:
          is_controller (bool): True if the device is the controller, false
                        if it's the responder.
          group (int): The group number of the controller button or the
                group number of the responding button.
          data (bytes[3]): Optional 3 byte data entry.  If this is None,
               defaults are returned.  Otherwise it must be a 3 element list.
               Any element that is not None is replaced with the default.

        Returns:
          bytes[3]: Returns a list of 3 bytes to use as D1,D2,D3.
        """
        # Most of this is from looking through Misterhouse bug reports.
        if is_controller:
            defaults = [0x03, 0x00, 0x01]

        # Responder data is always link dependent.  Since nothing was given,
        # assume the user wants to turn the device on (0xff).
        else:
            defaults = [0xff, 0x1f, 0x01]

        # For each field, use the input if not -1, else the default.
        return util.resolve_data3(defaults, data)

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
            ramp = 0x1f  # default
            if data[1] in self.ramp_pretty:
                ramp = self.ramp_pretty[data[1]]
            on_level = int((data[0] / .255) + .5) / 10
            ret = [{'on_level': on_level},
                   {'ramp_rate': ramp},
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
            if 'ramp_rate' in data:
                data_2 = 0x1f
                for ramp_key, ramp_value in self.ramp_pretty.items():
                    if data['ramp_rate'] >= ramp_value:
                        data_2 = ramp_key
                        break
            if 'on_level' in data:
                data_1 = int(data['on_level'] * 2.55 + .5)
        return [data_1, data_2, data_3]

    #-----------------------------------------------------------------------
    def get_flags(self, on_done=None):
        """Hijack base get_flags to inject extended flags request.

        The flags will be passed to the on_done callback as the data field.
        Derived types may do something with the flags by override the
        handle_flags method.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        seq = CommandSeq(self, "Dimmer get_flags complete", on_done,
                         name="GetFlags")
        seq.add(super().get_flags)
        seq.add(self._get_ext_flags)
        seq.run()

    #-----------------------------------------------------------------------
    def _get_ext_flags(self, on_done=None):
        """Get the Insteon operational extended flags field from the device.

        For the dimmer device, the flags include on-level and ramp-rate.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Dimmer %s cmd: get extended operation flags", self.label)

        # D1 = group (0x01), D2 = 0x00 == Data Request, others ignored,
        # per Insteon Dev Guide
        data = bytes([0x01] + [0x00] * 13)

        msg = Msg.OutExtended.direct(self.addr, Msg.CmdType.EXTENDED_SET_GET,
                                     0x00, data)
        msg_handler = handler.ExtendedCmdResponse(msg, self.handle_ext_flags,
                                                  on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_ext_flags(self, msg, on_done):
        """Handle replies to the _get_ext_flags command.

        Extended message payload is:
          D8 = on-level
          D7 = ramp-rate

        Args:
          msg (message.InpExtended):  The message reply.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
        """
        on_level = msg.data[7]
        self.db.set_meta('on_level', on_level)
        ramp_rate = msg.data[6]
        for ramp_key, ramp_value in self.ramp_pretty.items():
            if ramp_rate <= ramp_key:
                ramp_rate = ramp_value
                break
        LOG.ui("Dimmer %s on_level: %s (%.2f%%) ramp rate: %ss", self.label,
               on_level, on_level / 2.55, ramp_rate)
        on_done(True, "Operation complete", msg.data[5])

    #-----------------------------------------------------------------------
