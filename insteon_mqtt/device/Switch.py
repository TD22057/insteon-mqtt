#===========================================================================
#
# Insteon on/off device
#
#===========================================================================
from .Base import Base
from . import functions
from ..CommandSeq import CommandSeq
from .. import handler
from .. import log
from .. import message as Msg
from .. import on_off
from ..Signal import Signal
from .. import util

LOG = log.get_logger()


#===========================================================================
class Switch(functions.SetAndState, functions.Scene, Base):
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
        self.cmd_map.update({
            'set_flags' : self.set_flags,
            })

        # Update the group map with the groups to be paired and the handler
        # for broadcast messages from this group
        self.group_map.update({0x01: self.handle_on_off})

    #-----------------------------------------------------------------------
    def set_backlight(self, level, on_done=None):
        """Set the device backlight level.

        This changes the level of the LED back light that is used by the
        device status LED's (dimmer levels, KeypadLinc buttons, etc).

        The default factory level is 0x1f.

        Per page 157 of insteon dev guide range is between 0x11 and 0x7F,
        however in practice backlight can be incremented from 0x00 to at least
        0x7f.

        Args:
          level (int):  The backlight level in the range [0,255]
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        seq = CommandSeq(self, "Switch set backlight complete", on_done,
                         name="SetBacklight")

        # First set the backlight on or off depending on level value
        is_on = level > 0
        LOG.info("Switch %s setting backlight to %s", self.label, is_on)
        cmd = 0x09 if is_on else 0x08
        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd, bytes([0x00] * 14))
        msg_handler = handler.StandardCmd(msg, self.handle_backlight, on_done)
        seq.add_msg(msg, msg_handler)

        if is_on:
            # Second set the level only if on
            LOG.info("Switch %s setting backlight to %s", self.label, level)

            # Extended message data - see Insteon dev guide p156.
            data = bytes([
                0x01,   # D1 must be group 0x01
                0x07,   # D2 set global led brightness
                level,  # D3 brightness level
                ] + [0x00] * 11)

            msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)
            msg_handler = handler.StandardCmd(msg, self.handle_backlight,
                                              on_done)
            seq.add_msg(msg, msg_handler)

        seq.run()

    #-----------------------------------------------------------------------
    def set_flags(self, on_done, **kwargs):
        """Set internal device flags.

        This command is used to change internal device flags and states.
        Valid inputs are:

        - on_level=level: Change the default device on level (0-255) See
          set_on_level for details.

        Args:
          kwargs: Key=value pairs of the flags to change.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Switch %s cmd: set flags", self.label)

        # Check the input flags to make sure only ones we can understand were
        # passed in.
        FLAG_BACKLIGHT = "backlight"
        flags = set([FLAG_BACKLIGHT])
        unknown = set(kwargs.keys()).difference(flags)
        if unknown:
            LOG.error("Unknown Switch flags input: %s.\n Valid flags "
                      "are: %s", unknown, flags)

        # Start a command sequence so we can call the flag methods in series.
        seq = CommandSeq(self, "Switch set_flags complete", on_done,
                         name="DevSetFlags")

        if FLAG_BACKLIGHT in kwargs:
            backlight = util.input_byte(kwargs, FLAG_BACKLIGHT)
            seq.add(self.set_backlight, backlight)

        seq.run()

    #-----------------------------------------------------------------------
    def handle_backlight(self, msg, on_done):
        """Callback for handling set_backlight() responses.

        This is called when we get a response to the set_backlight() command.
        We don't need to do anything - just call the on_done callback with
        the status.

        Args:
          msg (InpStandard):  The response message from the command.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        on_done(True, "Backlight level updated", None)

    #-----------------------------------------------------------------------
    def handle_on_off(self, msg):
        """Handle broadcast messages from this device.

        This is called from base.handle_broadcast using the group_cmd map.

        Args:
          msg (InpStandard): Broadcast message from the device.
        """
        # If we have a saved reason from a simulated scene command, use that.
        # Otherwise the device button was pressed.
        reason = self.broadcast_reason if self.broadcast_reason else \
                 on_off.REASON_DEVICE
        self.broadcast_reason = ""

        # On/off command codes.
        if on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)
            LOG.info("Switch %s broadcast grp: %s on: %s mode: %s", self.addr,
                     msg.group, is_on, mode)

            # For an on command, we can update directly.
            if is_on:
                self._set_state(is_on=True, mode=mode, reason=reason)

            else:
                self._set_state(is_on=False, mode=mode, reason=reason)

        # Starting or stopping manual mode.
        elif on_off.Manual.is_valid(msg.cmd1):
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

        # This will find all the devices we're the controller of for this
        # group and call their handle_group_cmd() methods to update their
        # states since they will have seen the group broadcast and updated
        # (without sending anything out).
        self.update_linked_devices(msg)

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        """Callback for handling refresh() responses.

        This is called when we get a response to the refresh() command.  The
        refresh command reply will contain the current device state in cmd2
        and this updates the device with that value.  It is called by
        handler.DeviceRefresh when we can an ACK for the refresh command.

        Args:
          msg (message.InpStandard):  The refresh message reply.  The current
              device state is in the msg.cmd2 field.
        """
        LOG.ui("Switch %s refresh on=%s", self.label, msg.cmd2 > 0x00)

        # Current on/off level is stored in cmd2 so update our level.
        self._set_state(is_on=msg.cmd2 > 0x00, reason=on_off.REASON_REFRESH)

    #-----------------------------------------------------------------------
    def handle_group_cmd(self, addr, msg):
        """Respond to a group command for this device.

        This is called when this device is a responder to a scene.  The
        device that received the broadcast message (handle_broadcast) will
        call this method for every device that is linked to it.  The device
        should look up the responder entry for the group in it's all link
        database and update it's state accordingly.

        Args:
          addr (Address):  The device that sent the message.  This is the
               controller in the scene.
          msg (InpStandard):  Broadcast message from the device.  Use
              msg.group to find the group and msg.cmd1 for the command.
        """
        # Make sure we're really a responder to this message.  This shouldn't
        # ever occur.
        entry = self.db.find(addr, msg.group, is_controller=False)
        if not entry:
            LOG.error("Switch %s has no group %s entry from %s", self.addr,
                      msg.group, addr)
            return

        # Handle on/off commands codes.
        if on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)
            self._set_state(is_on=is_on, mode=mode, reason=on_off.REASON_SCENE)

        # Note: I don't believe the on/off switch can participate in manual
        # mode stopping commands since it changes state when the button is
        # held, not when it's released.
        else:
            LOG.warning("Switch %s unknown group cmd %#04x", self.addr,
                        msg.cmd1)

    #-----------------------------------------------------------------------
