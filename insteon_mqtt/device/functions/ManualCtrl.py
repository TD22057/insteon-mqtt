#===========================================================================
#
# ManualCtrl Functions.
#
#===========================================================================
from ..base import Base
from ... import log
from ... import on_off
from ...Signal import Signal


LOG = log.get_logger()


class ManualCtrl(Base):
    """Manual Control Trait Abstract Class

    This is an abstract class that provides support for devices which can
    broadcast manual commands.  Interestingly, non-dimmable devices can
    emit manual commands, but they do not respond to them.  As a result, the
    breakdown of manual feature is a little weird in our class structure.

    Again, this class provides support for devices that emit manual control
    messages, but it does not provide support for responding to manual.
    The abstract support for responding to manual commands is in Responder
    and the main functions for devices that support responding to manual
    commands is in DimmerBase.

    DimmerBase inherits from this class.  If an object inherits from
    DimmerBase, it SHOULD NOT ALSO INHERIT FROM THIS CLASS.

    The MQTT topic for manual messages is disabled by default.  But a device
    that has been affected by a manual command will be refresh()'d when the
    Manual.STOP command is sent, causing the state of that device to be
    updated.

    - signal_manual( Device, on_off.Manual mode, str reason ): Sent when the
      device starts or stops manual mode (when a button is held down or
      released).
    """
    def __init__(self, protocol, modem, address, name=None, config_extra=None):
        """Constructor

        Args:
          protocol (Protocol): The Protocol object used to communicate
                   with the Insteon network.  This is needed to allow the
                   device to send messages to the PLM modem.
          modem (Modem): The Insteon modem used to find other devices.
          address (Address): The address of the device.
          name (str): Nice alias name to use for the device.
          config_extra (dict): Extra configuration settings
        """
        super().__init__(protocol, modem, address, name, config_extra)

        # Manual mode start up, down, off
        # API: func(Device, on_off.Manual mode, str reason)
        self.signal_manual = Signal()

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
        LOG.info("Device %s grp: %s manual change %s", self.addr, msg.group,
                 manual)
        self.signal_manual.emit(self, button=msg.group, manual=manual,
                                reason=reason)
        self.react_to_manual(manual, msg.group, reason)

    #-----------------------------------------------------------------------
    def react_to_manual(self, manual, group, reason):
        """React to Manual Mode Received from the Device

        Non-dimmable devices react immediatly when issueing a manual command
        while dimmable devices slowly ramp on. This function is here to
        provide DimmerBase a place to alter the default functionality. This
        function should call _set_state() at the appropriate times to update
        the state of the device.

        Args:
          manual (on_off.Manual):  The manual command type
          group (int):  The group sending the command
          reason (str):  The reason string to pass on
        """
        # Switches change state when the switch is held (not all devices
        # do this).
        if manual == on_off.Manual.UP:
            self._set_state(is_on=True, group=group, mode=on_off.Mode.MANUAL,
                            reason=reason)
        elif manual == on_off.Manual.DOWN:
            self._set_state(is_on=False, group=group, mode=on_off.Mode.MANUAL,
                            reason=reason)
