#===========================================================================
#
# Insteon on/off device
#
#===========================================================================
from .Base import Base
from .functions import Responder, Scene, Backlight
from .. import log
from .. import on_off
from ..Signal import Signal

LOG = log.get_logger()


#===========================================================================
class Switch(Responder, Scene, Backlight, Base):
    """Insteon on/off switch device.

    This class can be used to model any device that acts like a on/off switch
    including wall switches, lamp modules, and appliance modules.

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).  Supported signals are:

    - signal_state( Device, bool is_on, on_off.Mode mode, str reason ):
      Sent whenever the switch is turned on or off.

    - signal_manual( Device, on_off.Manual mode ): Sent when the device
      starts or stops manual mode (when a button is held down or released).
    """
    def __init__(self, protocol, modem, address, name=None):
        """Constructor

        Args:
          protocol (Protocol):  The Protocol object used to communicate
                   with the Insteon network.  This is needed to allow the
                   device to send messages to the PLM modem.
          modem (Modem):  The Insteon modem used to find other devices.
          address (Address):  The address of the device.
          name (str):  Nice alias name to use for the device.
        """
        super().__init__(protocol, modem, address, name)

        # Manual mode start up, down, off
        # API: func(Device, on_off.Manual mode)
        self.signal_manual = Signal()

        # Remote (mqtt) commands mapped to methods calls.  Add to the base
        # class defined commands.
        # self.cmd_map.update({
        #     })

        # Update the group map with the groups to be paired and the handler
        # for broadcast messages from this group
        self.group_map.update({0x01: self.handle_on_off})

    #-----------------------------------------------------------------------
    def process_manual(self, msg, reason):
        """Handle Manual Mode Received from the Device

        This is called as part of the handle_broadcast response.  It
        processes the manual mode changes sent by the device.

        Args:
          msg (InpStandard):  Broadcast message from the device.  Use
              msg.group to find the group and msg.cmd1 for the command.
          reason (str):  The reason string to pass on
        """
        manual = on_off.Manual.decode(msg.cmd1, msg.cmd2)
        LOG.info("Switch %s manual change %s", self.addr, manual)

        self.signal_manual.emit(self, manual=manual)

        # Switches change state when the switch is held (not all devices
        # do this).
        if manual == on_off.Manual.UP:
            self._set_state(is_on=True, mode=on_off.Mode.MANUAL,
                            reason=reason)
        elif manual == on_off.Manual.DOWN:
            self._set_state(is_on=False, mode=on_off.Mode.MANUAL,
                            reason=reason)

    #-----------------------------------------------------------------------
