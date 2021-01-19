#===========================================================================
#
# Insteon on/off outlet
#
#===========================================================================
import functools
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


class Outlet(functions.SetAndState, Base):
    """Insteon on/off outlet device.

    This is used for in-wall on/off outlets.  Each outlet (top and bottom) is
    an independent switch and is controlled via group 1 (top) and group2
    (bottom) inputs.

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).  Supported signals are:

    - signal_state( Device, int group, bool is_on, on_off.Mode mode, str
                     reason ): Sent whenever the switch is turned on or off.
                     Group will be 1 for the top outlet and 2 for the bottom
                     outlet.
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

        self._is_on = [False, False]  # top outlet, bottom outlet

        # Support on/off style signals.
        # API: func(Device, int group, bool is_on, on_off.Mode mode,
        #           str reason)
        self.signal_state = Signal()

        # Remote (mqtt) commands mapped to methods calls.  Add to the
        # base class defined commands.
        self.cmd_map.update({
            'set_flags' : self.set_flags,
            })

        # NOTE: the outlet does NOT include the group in the ACK of an on/off
        # command.  So there is no way to tell which outlet is being ACK'ed
        # if we send multiple messages to it.  Each time on or off is called,
        # it pushes the outlet to this list so that when the ACK/NAK arrives,
        # we can pop it off and know which outlet was being commanded.
        self._which_outlet = []

        # Update the group map with the groups to be paired and the handler
        # for broadcast messages from this group
        # Can the outlet really act as a controller?
        self.group_map.update({0x01: self.handle_on_off,
                               0x02: self.handle_on_off})

        # List of responder group numbers
        self.responder_groups = [0x01, 0x02]

    #-----------------------------------------------------------------------
    def refresh(self, force=False, on_done=None):
        """Refresh the current device state and database if needed.

        This sends a ping to the device.  The reply has the current device
        state (on/off, level, etc) and the current db delta value which is
        checked against the current db value.  If the current db is out of
        date, it will trigger a download of the database.

        This will send out an updated signal for the current device status
        whenever possible (like dimmer levels).

        Args:
          force (bool):  If true, will force a refresh of the device database
                even if the delta value matches as well as a re-query of the
                device model information even if it is already known.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Outlet %s cmd: status refresh", self.label)

        seq = CommandSeq(self, "Device refreshed", on_done, name="DevRefresh")

        # This sends a refresh ping which will respond w/ the current
        # database delta field.  The handler checks that against the current
        # value.  If it's different, it will send a database download command
        # to the device to update the database.  Code 0x19 also allows us to
        # get the state of both outlets in a single field.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x01)
        msg_handler = handler.DeviceRefresh(self, self.handle_refresh, force,
                                            on_done, num_retry=3)
        seq.add_msg(msg, msg_handler)

        # If model number is not known, or force true, run get_model
        self.addRefreshData(seq, force)

        # Run all the commands.
        seq.run()

    #-----------------------------------------------------------------------
    def on(self, group=0x01, level=None, mode=on_off.Mode.NORMAL,
           reason="", transition=None, on_done=None):
        """Turn the device on.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group (int):  The group to send the command to.  The top outlet is
                group 1, the bottom outlet is group 2.
          level (int):  If non zero, turn the device on.  Should be in the
                range 0 to 255.  Only dimmers use the intermediate values, all
                other devices look at level=0 or level>0.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # See __init__ code comments for what this is for.
        self._which_outlet.append(group)

        # Bottom outlet uses an extended message
        if group == 2:
            cmd1, cmd2 = self.cmd_on_values(mode, level, transition, group)
            data = bytes([0x02] + [0x00] * 13)
            msg = Msg.OutExtended.direct(self.addr, cmd1, cmd2, data)
            callback = functools.partial(self.handle_ack, reason=reason)
            msg_handler = handler.StandardCmd(msg, callback, on_done)
            self.send(msg, msg_handler)
        else:
            # Top outlet uses a regular on command pass to SetAndState
            super().on(group=group, level=level, mode=mode, reason=reason,
                       transition=transition, on_done=on_done)

    #-----------------------------------------------------------------------
    def off(self, group=0x01, mode=on_off.Mode.NORMAL, reason="",
            transition=None, on_done=None):
        """Turn the device off.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group (int):  The group to send the command to.  The top outlet is
                group 1, the bottom outlet is group 2.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # See __init__ code comments for what this is for.
        self._which_outlet.append(group)

        # Bottom outlet uses an extended message
        if group == 2:
            cmd1, cmd2 = self.cmd_off_values(mode, transition, group)
            data = bytes([0x02] + [0x00] * 13)
            msg = Msg.OutExtended.direct(self.addr, cmd1, cmd2, data)
            callback = functools.partial(self.handle_ack, reason=reason)
            msg_handler = handler.StandardCmd(msg, callback, on_done)
            self.send(msg, msg_handler)
        else:
            # Top outlet uses a regular on command pass to SetAndState
            super().off(group=group, mode=mode, reason=reason,
                        transition=transition, on_done=on_done)

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
        seq = CommandSeq(self, "Outlet set backlight complete", on_done,
                         name="SetBacklight")

        # First set the backlight on or off depending on level value
        is_on = level > 0
        LOG.info("Outlet %s setting backlight to %s", self.label, is_on)
        cmd = 0x09 if is_on else 0x08
        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd, bytes([0x00] * 14))
        callback = self.generic_ack_callback("Backlight on: %s" % is_on)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        seq.add_msg(msg, msg_handler)

        if is_on:
            # Second set the level only if on
            LOG.info("Outlet %s setting backlight to %s", self.label, level)

            # Extended message data - see Insteon dev guide p156.
            data = bytes([
                0x01,   # D1 must be group 0x01
                0x07,   # D2 set global led brightness
                level,  # D3 brightness level
                ] + [0x00] * 11)

            msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)
            callback = self.generic_ack_callback("Backlight level updated.")
            msg_handler = handler.StandardCmd(msg, callback, on_done)
            seq.add_msg(msg, msg_handler)

        seq.run()

    #-----------------------------------------------------------------------
    def set_flags(self, on_done, **kwargs):
        """Set internal device flags.

        This command is used to change internal device flags and states.
        Valid inputs are:

        - backlight=level:  Change the backlight LED level (0-255).  See
          set_backlight() for details.

        Args:
          kwargs: Key=value pairs of the flags to change.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Outlet %s cmd: set flags", self.label)

        # Check the input flags to make sure only ones we can understand were
        # passed in.
        FLAG_BACKLIGHT = "backlight"
        flags = set([FLAG_BACKLIGHT])
        unknown = set(kwargs.keys()).difference(flags)
        if unknown:
            LOG.error("Unknown Outlet flags input: %s.\n Valid flags "
                      "are: %s", unknown, flags)

        # Start a command sequence so we can call the flag methods in series.
        seq = CommandSeq(self, "Outlet set_flags complete", on_done,
                         name="DevSetFlags")

        if FLAG_BACKLIGHT in kwargs:
            backlight = util.input_byte(kwargs, FLAG_BACKLIGHT)
            seq.add(self.set_backlight, backlight)

        seq.run()

    #-----------------------------------------------------------------------
    def handle_on_off(self, msg):
        """Handle broadcast on_off messages from this device.

        This is called via the handle_broadcast and the mapping in group_map.

        Args:
          msg (InpStandard):  Broadcast message from the device.
        """
        reason = on_off.REASON_DEVICE
        # On/off command codes.
        if on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)
            LOG.info("Outlet %s broadcast grp: %s on: %s mode: %s", self.addr,
                     msg.group, is_on, mode)

            self._set_state(group=msg.group, is_on=is_on, mode=mode,
                            reason=reason)

            self.update_linked_devices(msg)

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg, group=None):
        """Callback for handling refresh() responses.

        This is called when we get a response to the refresh() command.  The
        refresh command reply will contain the current device state in cmd2
        and this updates the device with that value.  It is called by
        handler.DeviceRefresh when we can an ACK for the refresh command.

        Args:
          msg (message.InpStandard):  The refresh message reply.  The current
              device state is in the msg.cmd2 field.
        """
        # From outlet developers guide - refresh must be 0x19 0x01 to enable
        # these codes which allows us to get the state of both outlets with
        # one call.
        response = {
            0x00: [False, False],
            0x01: [True, False],
            0x02: [False, True],
            0x03: [True, True]
            }

        is_on = response.get(msg.cmd2, None)
        if is_on is not None:
            LOG.ui(" %s refresh top=%s bottom=%s", self.label, is_on[0],
                   is_on[1])

            # Set the state for each outlet.
            self._set_state(group=1, is_on=is_on[0],
                            reason=on_off.REASON_REFRESH)
            self._set_state(group=2, is_on=is_on[1],
                            reason=on_off.REASON_REFRESH)

        else:
            LOG.error("Outlet %s unknown refresh response %s", self.label,
                      msg.cmd2)

    #-----------------------------------------------------------------------
    def decode_on_level(self, cmd1, cmd2):
        """Callback for standard commanded messages.

        Decodes the cmds recevied from the device into is_on, level, and mode
        to be consumed by _set_state().

        Args:
          cmd1 (byte): The command 1 value
          cmd2 (byte): The command 2 value
        Returns:
          is_on (bool): Is the device on.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          level (int): On level between 0-255.
          group (int): The group number that this state applies to. Defaults
                       to None.
        """
        # Default Returns
        group = None
        is_on = None
        level = None
        mode = on_off.Mode.NORMAL

        # Get the last outlet we were commanding.  The message doesn't tell
        # us which outlet it was so we have to track it here.  See __init__
        # code comments for more info.
        if not self._which_outlet:
            LOG.error("Outlet %s ACK error.  No outlet ID's were saved",
                      self.addr)
        else:
            group = self._which_outlet.pop(0)
            is_on, mode = on_off.Mode.decode(cmd1)
        return (is_on, level, mode, group)

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
            LOG.error("Outlet %s has no group %s entry from %s", self.addr,
                      msg.group, addr)
            return

        # The local button being modified is stored in the db entry.
        localGroup = entry.data[2]

        # Handle on/off commands codes.
        if on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)
            self._set_state(group=localGroup, is_on=is_on, mode=mode,
                            reason=on_off.REASON_SCENE)

        # Note: I don't believe the on/off switch can participate in manual
        # mode stopping commands since it changes state when the button is
        # held, not when it's released.
        else:
            LOG.warning("Outlet %s unknown group cmd %#04x", self.addr,
                        msg.cmd1)

    #-----------------------------------------------------------------------
    def _cache_state(self, group, is_on, level, reason):
        """Cache the State of the Device

        Used to help with the unique device functions.

        Args:
          group (int): The group which this applies
          is_on (bool): Whether the device is on.
          level (int): The new device level in the range [0,255].  0 is off.
          reason (str): Reason string to pass around.
        """
        self._is_on[group - 1] = is_on

    #-----------------------------------------------------------------------
