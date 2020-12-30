#===========================================================================
#
# Insteon on/off device
#
#===========================================================================
import functools
from .Base import Base
from ..CommandSeq import CommandSeq
from .. import handler
from .. import log
from .. import message as Msg
from .. import on_off
from ..Signal import Signal
from .. import util

LOG = log.get_logger()


#===========================================================================
class Switch(Base):
    """Insteon on/off switch device.

    This class can be used to model any device that acts like a on/off switch
    including wall switches, lamp modules, and appliance modules.

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).  Supported signals are:

    - signal_on_off( Device, bool is_on, on_off.Mode mode, str reason ):
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

        self._is_on = False

        # Support on/off style signals.
        # API: func(Device, bool is_on, on_off.Mode mode, str reason)
        self.signal_on_off = Signal()

        # Manual mode start up, down, off
        # API: func(Device, on_off.Manual mode)
        self.signal_manual = Signal()

        # Remote (mqtt) commands mapped to methods calls.  Add to the base
        # class defined commands.
        self.cmd_map.update({
            'on' : self.on,
            'off' : self.off,
            'set' : self.set,
            'scene' : self.scene,
            'set_flags' : self.set_flags,
            })

        # Special callback to run when receiving a broadcast clean up.  See
        # scene() for details.
        self.broadcast_done = None
        self.broadcast_reason = ""

        # Update the group map with the groups to be paired and the handler
        # for broadcast messages from this group
        self.group_map.update({0x01: self.handle_on_off})

    #-----------------------------------------------------------------------
    def on(self, group=0x01, level=None, mode=on_off.Mode.NORMAL, reason="",
           on_done=None):
        """Turn the device on.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group (int):  The group to send the command to.  For switches this
                this must be 1.  Allowing a group here gives us a consistent
                API to the on command across devices.
          level (int):  If non-zero, turn the device on.  The API is an int
                to keep a consistent API with other devices.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Switch %s cmd: on %s", self.addr, mode)
        assert group == 0x01
        assert isinstance(mode, on_off.Mode)

        # Send the requested on code value.
        cmd1 = on_off.Mode.encode(True, mode)
        msg = Msg.OutStandard.direct(self.addr, cmd1, 0xff)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_ack, reason=reason)
        msg_handler = handler.StandardCmd(msg, callback, on_done)

        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def off(self, group=0x01, mode=on_off.Mode.NORMAL, reason="",
            on_done=None):
        """Turn the device off.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group (int):  The group to send the command to.  For this device,
                this must be 1.  Allowing a group here gives us a consistent
                API to the on command across devices.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Switch %s cmd: off %s", self.addr, mode)
        assert group == 0x01
        assert isinstance(mode, on_off.Mode)

        # Send an off or instant off command.
        cmd1 = on_off.Mode.encode(False, mode)
        msg = Msg.OutStandard.direct(self.addr, cmd1, 0x00)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_ack, reason=reason)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set(self, level, group=0x01, mode=on_off.Mode.NORMAL, reason="",
            on_done=None):
        """Turn the device on or off.  Level zero will be off.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          level (int):  If non-zero, turn the device on.  The API is an int
                to keep a consistent API with other devices.
          group (int):  The group to send the command to.  For switches this
                this must be 1.  Allowing a group here gives us a consistent
                API to the on command across devices.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        if level:
            self.on(group, level, mode, reason, on_done)
        else:
            self.off(group, mode, reason, on_done)

    #-----------------------------------------------------------------------
    def scene(self, is_on, group=0x01, reason="", on_done=None):
        """Trigger a scene on the device.

        Triggering a scene is the same as simulating a button press on the
        device.  It will change the state of the device and notify responders
        that are linked ot the device to be updated.

        Args:
          is_on (bool):  True for an on command, False for an off command.
          group (int):  The group on the device to simulate.  For this device,
                this must be 1.
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Switch %s scene %s", self.addr, "on" if is_on else "off")
        assert group == 0x01

        # Send an 0x30 all link command to simulate the button being pressed
        # on the switch.  See page 163 of insteon dev guide
        cmd1 = 0x11 if is_on else 0x13
        data = bytes([
            group,  # D1 = group (button)
            0x00,   # D2 = use level in scene db
            0x00,   # D3 = on level if D2=0x01
            cmd1,   # D4 = cmd1 to send
            0x00,   # D5 = cmd2 to send
            0x00,   # D6 = use ramp rate in scene db
            ] + [0x00] * 8)
        msg = Msg.OutExtended.direct(self.addr, 0x30, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        done_callback = on_done if is_on else None
        callback = functools.partial(self.handle_scene, reason=reason)
        msg_handler = handler.StandardCmd(msg, callback, done_callback)
        self.send(msg, msg_handler)

        # Scene triggering will not turn the device off (no idea why), so we
        # have to send an explicit off command to do that.  If this is None,
        # we're triggering a scene and so should bypass the normal
        # handle_broadcast logic to take this case into account.  Note that
        # if we sent and off command either before or after the ACK of the
        # command above, it doesn't work - we have to wait until the
        # broadcast msg is finished.
        if not is_on:
            self.broadcast_done = \
                functools.partial(self.off, group=group, on_done=on_done,
                                  reason=reason)

    #-----------------------------------------------------------------------
    def set_backlight(self, level, on_done=None):
        """Set the device backlight level.

        This changes the level of the LED back light that is used by the
        device status LED's (dimmer levels, KeypadLinc buttons, etc).

        The default factory level is 0x1f.

        Args:
          level (int):  The backlight level in the range [0,255]
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Switch %s setting backlight to %s", self.label, level)

        # Bound to 0x11 <= level <= 0xff per page 157 of insteon dev guide.
        # 0x00 is used to disable the backlight so allow that explicitly.
        if level:
            level = max(0x11, min(level, 0xff))

        # Extended message data - see Insteon dev guide p156.
        data = bytes([
            0x01,   # D1 must be group 0x01
            0x07,   # D2 set global led brightness
            level,  # D3 brightness level
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        msg_handler = handler.StandardCmd(msg, self.handle_backlight, on_done)

        self.send(msg, msg_handler)

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
            raise Exception("Unknown Switch flags input: %s.\n Valid flags "
                            "are: %s" % unknown, flags)

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

        # ACK of the broadcast.  Ignore this unless we sent a simulated off
        # scene in which case run the broadcast done handler.  This is a
        # weird special case - see scene() for details.
        if msg.cmd1 == Msg.CmdType.LINK_CLEANUP_REPORT:
            LOG.info("Switch %s broadcast ACK grp: %s", self.addr, msg.group)

            if self.broadcast_done:
                self.broadcast_done()
            self.broadcast_done = None
            return

        # On/off command codes.
        elif on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)
            LOG.info("Switch %s broadcast grp: %s on: %s mode: %s", self.addr,
                     msg.group, is_on, mode)

            # For an on command, we can update directly.
            if is_on:
                self._set_is_on(True, mode, reason)

            # For an off command, we need to see if broadcast_done is active.
            # This is a generated broadcast and we need to manually turn the
            # device off so don't update it's state until that occurs.
            elif not self.broadcast_done:
                self._set_is_on(False, mode, reason)

        # Starting or stopping manual mode.
        elif on_off.Manual.is_valid(msg.cmd1):
            manual = on_off.Manual.decode(msg.cmd1, msg.cmd2)
            LOG.info("Switch %s manual change %s", self.addr, manual)

            self.signal_manual.emit(self, manual)

            # Switches change state when the switch is held (not all devices
            # do this).
            if manual == on_off.Manual.UP:
                self._set_is_on(True, on_off.Mode.MANUAL, reason)
            elif manual == on_off.Manual.DOWN:
                self._set_is_on(False, on_off.Mode.MANUAL, reason)

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
        self._set_is_on(msg.cmd2 > 0x00, reason=on_off.REASON_REFRESH)

    #-----------------------------------------------------------------------
    def handle_ack(self, msg, on_done, reason=""):
        """Callback for standard commanded messages.

        This callback is run when we get a reply back from one of our
        commands to the device.  If the command was ACK'ed, we know it worked
        so we'll update the internal state of the device and emit the signals
        to notify others of the state change.

        Args:
          msg (message.InpStandard):  The reply message from the device.
              The on/off level will be in the cmd2 field.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
        """
        # If this it the ACK we're expecting, update the internal state and
        # emit our signals.
        LOG.debug("Switch %s ACK: %s", self.addr, msg)

        is_on, mode = on_off.Mode.decode(msg.cmd1)
        reason = reason if reason else on_off.REASON_COMMAND
        self._set_is_on(is_on, mode, reason)
        on_done(True, "Switch state updated to on=%s" % self._is_on,
                self._is_on)

    #-----------------------------------------------------------------------
    def handle_scene(self, msg, on_done, reason=""):
        """Callback for scene simulation commanded messages.

        This callback is run when we get a reply back from triggering a scene
        on the device.  If the command was ACK'ed, we know it worked.  The
        device will then send out standard broadcast messages which will
        trigger other updates for the scene devices.

        Args:
          msg (message.InpStandard): The reply message from the device.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
        """
        # Call the callback.  We don't change state here - the device will
        # send a regular broadcast message which will run handle_broadcast
        # which will then update the state.
        LOG.debug("Switch %s ACK: %s", self.addr, msg)

        # Reason is device because we're simulating a button press.  We
        # can't really pass this around because we just get a broadcast
        # message later from the device.  So we set a temporary variable
        # here and use it in handle_broadcast() to output the reason.
        self.broadcast_reason = reason if reason else on_off.REASON_DEVICE
        on_done(True, "Scene triggered", None)

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
            self._set_is_on(is_on, mode, on_off.REASON_SCENE)

        # Note: I don't believe the on/off switch can participate in manual
        # mode stopping commands since it changes state when the button is
        # held, not when it's released.
        else:
            LOG.warning("Switch %s unknown group cmd %#04x", self.addr,
                        msg.cmd1)

    #-----------------------------------------------------------------------
    def _set_is_on(self, is_on, mode=on_off.Mode.NORMAL, reason=""):
        """Update the device on/off state.

        This will change the internal state and emit the state changed
        signals.  It is called by whenever we're informed that the device has
        changed state.

        Args:
          is_on (bool):  True if the switch is on, False if it isn't.
          mode (on_off.Mode): The type of on/off that was triggered (normal,
               fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
        """
        LOG.info("Setting device %s on %s %s %s", self.label, is_on,
                 mode, reason)
        self._is_on = bool(is_on)

        self.signal_on_off.emit(self, self._is_on, mode, reason)

    #-----------------------------------------------------------------------
