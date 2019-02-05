#===========================================================================
#
# KeypadLinc module
#
#===========================================================================
import functools
from ..CommandSeq import CommandSeq
from .. import handler
from .. import log
from .. import message as Msg
from .. import on_off
from ..Signal import Signal
from .. import util
from .Base import Base

LOG = log.get_logger()


class KeypadLinc(Base):
    """Insteon KeypadLinc switch or dimmer plus remote module

    TODO: docs

    Each button (up to 8) has an LED light.  Light status can be retrieved by
    sending 0x19 0x01 which returns cmd1=db delta and cmd2=LED bit flags.
    """

    #-----------------------------------------------------------------------
    def __init__(self, protocol, modem, address, name, dimmer=True):
        """Constructor

        Args:
          protocol:    (Protocol) The Protocol object used to communicate
                       with the Insteon network.  This is needed to allow
                       the device to send messages to the PLM modem.
          modem:       (Modem) The Insteon modem used to find other devices.
          address:     (Address) The address of the device.
          name:        (str) Nice alias name to use for the device.
          dimmer:      (bool) True if the device supports dimming - False if
                       it's a regular switch.
        """
        super().__init__(protocol, modem, address, name)

        # Switch or dimmer type.
        self.is_dimmer = dimmer
        self.type_name = "keypad_linc" if dimmer else "keypad_linc_sw"

        # Group on/off signal.
        # API: func(Device, int group, int level, on_off.Mode mode)
        self.signal_active = Signal()

        # Manual mode start up, down, off
        # API: func(Device, int group, on_off.Manual mode)
        self.signal_manual = Signal()

        # Remote (mqtt) commands mapped to methods calls.  Add to the
        # base class defined commands.
        self.cmd_map.update({
            'on' : self.on,
            'off' : self.off,
            'set' : self.set,
            'scene' : self.scene,
            'set_flags' : self.set_flags,
            'set_button_led' : self.set_button_led,
            })

        if self.is_dimmer:
            self.cmd_map.update({
                'increment_up' : self.increment_up,
                'increment_down' : self.increment_down,
                })

        # Special callback to run when receiving a broadcast clean up.  See
        # scene() for details.
        self.broadcast_done = None

        # 8 bits representing the LED's on the device for buttons 1-8.  For
        # buttons 2-8 (8 button keypad) and 3-6 (6 button keypad), these also
        # represent the state of the switch on vs off.  The load controller
        # button (1 on 8 btn and 1,2,7,8 on 6 btn), cannot be controlled by
        # changing the led state - only toggling the load changes the state.
        # Since the non-load buttons have nothing to switch, the led state is
        # the state of the switch.
        self._led_bits = 0x00

        # Button 1 level (0-255)
        self._level = 0

    #-----------------------------------------------------------------------
    def pair(self, on_done=None):
        """Pair the device with the modem.

        This only needs to be called one time.  It will set the device as a
        controller and the modem as a responder so the modem will see group
        broadcasts and report them to us.

        The device must already be a responder to the modem (push set on the
        modem, then set on the device) so we can update it's database.
        """
        LOG.info("KeypadLinc %s pairing", self.addr)

        # Build a sequence of calls to the do the pairing.  This insures each
        # call finishes and works before calling the next one.  We have to do
        # this for device db manipulation because we need to know the memory
        # layout on the device before making changes.
        seq = CommandSeq(self.protocol, "KeypadLinc paired", on_done)

        # Start with a refresh command - since we're changing the db, it must
        # be up to date or bad things will happen.
        seq.add(self.refresh)

        # Add the device as a responder to the modem on group 1.  This is
        # probably already there - and maybe needs to be there before we can
        # even issue any commands but this check insures that the link is
        # present on the device and the modem.
        seq.add(self.db_add_resp_of, 0x01, self.modem.addr, 0x01,
                refresh=False)

        # Now add the device as the controller of the modem for all 8
        # buttons.  If this is a 6 button keypad, the extras will go unused
        # but won't hurt anything.  This lets the modem receive updates about
        # the button presses and state changes.
        for group in range(1, 9):
            seq.add(self.db_add_ctrl_of, group, self.modem.addr, group,
                    refresh=False)

        # Also add the modem as a controller for the buttons - this lets the
        # modem issue simulated scene commands to those buttons.
        for group in range(1, 9):
            seq.add(self.db_add_resp_of, group, self.modem.addr, group,
                    refresh=False)

        # Finally start the sequence running.  This will return so the
        # network event loop can process everything and the on_done callbacks
        # will chain everything together.
        seq.run()

    #-----------------------------------------------------------------------
    def refresh(self, force=False, on_done=None):
        """TODO doc
        """
        # Send a 0x19 0x01 command to get the LED light on/off flags.
        LOG.info("KeypadLinc %s cmd: keypad status refresh", self.addr)

        seq = CommandSeq(self.protocol, "Refresh complete", on_done)

        # This sends a refresh ping which will respond w/ the LED bit flags
        # (1-8) and current database delta field.  Pass skip_db here - we'll
        # let the dimmer refresh handler above take care of getting the
        # database updated.  Otherwise this handler and the one created in
        # the dimmer refresh would download the database twice.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x01)
        msg_handler = handler.DeviceRefresh(self, self.handle_led_refresh,
                                            force=False, num_retry=3,
                                            skip_db=True)
        seq.add_msg(msg, msg_handler)

        # If we get the LED state correctly, then have the base also get it's
        # state and update the database if necessary.  This also calls
        # handle_refresh to set the group 1 level.
        seq.add(Base.refresh, self, force)

        seq.run()

    #-----------------------------------------------------------------------
    def on(self, group=1, level=0xff, mode=on_off.Mode.NORMAL, on_done=None):
        """Turn the device on.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group:    (int) The group number to set.  1 is the load.  Must be
                    in the range 1-8 inclusive.
          level:    (int) If non zero, turn the device on.  Should be
                    in the range 0x00 to 0xff.
          instant:  (bool) False for a normal ramping change, True for an
                    instant change.
        """
        LOG.info("KeypadLinc %s cmd: on %s", self.addr, level)
        assert 1 <= group <= 8
        assert level >= 0 and level <= 0xff
        assert isinstance(mode, on_off.Mode)

        # Non-load buttons are turned on/off via the LED command.
        if group != 1:
            self.set_button_led(group, True, on_done)

        # Group 1 uses a direct command to set the level.
        else:
            # For switches, on is always full level
            if not self.is_dimmer:
                level = 0xff

            # Send the correct on code.
            cmd1 = on_off.Mode.encode(True, mode)
            msg = Msg.OutStandard.direct(self.addr, cmd1, level)

            # Use the standard command handler which will notify us when the
            # command is ACK'ed.
            msg_handler = handler.StandardCmd(msg, self.handle_ack, on_done)

            # Send the message to the PLM modem for protocol.
            self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def off(self, group=1, mode=on_off.Mode.NORMAL, on_done=None):
        """Turn the device off.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group:    (int) The group number to set.  1 is the load.  Must be
                    in the range 1-8 inclusive.
          instant:  (bool) False for a normal ramping change, True for an
                    instant change.
        """
        LOG.info("KeypadLinc %s cmd: off", self.addr)
        assert 1 <= group <= 8
        assert isinstance(mode, on_off.Mode)

        # Non-load buttons are turned on/off via the LED command.
        if group != 1:
            self.set_button_led(group, False, on_done)

        # Group 1 uses a direct command to set the level.
        else:
            # Send an off or instant off command.
            cmd1 = on_off.Mode.encode(True, mode)
            msg = Msg.OutStandard.direct(self.addr, cmd1, 0x00)

            # Use the standard command handler which will notify us when the
            # command is ACK'ed.
            msg_handler = handler.StandardCmd(msg, self.handle_ack, on_done)

            # Send the message to the PLM modem for protocol.
            self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set(self, level, group=1, mode=on_off.Mode.NORMAL, on_done=None):
        """Set the device on or off.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          level:    (int/bool) If non zero, turn the device on.  Should be
                    in the range 0x00 to 0xff.  If True, the level will be
                    0xff.
          group:    (int) The group number to set.  1 is the load.  Must be
                    in the range 1-8 inclusive.
          instant:  (bool) False for a normal ramping change, True for an
                    instant change.
        """
        if level:
            self.on(group, level, mode, on_done)
        else:
            self.off(group, mode, on_done)

    #-----------------------------------------------------------------------
    def increment_up(self, on_done=None):
        """Increment the current level up.

        Levels increment in units of 8 (32 divisions from off to on).

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.
        """
        if not self.is_dimmer:
            LOG.error("KeypadLinc %s switch doesn't support increment up "
                      "command", self.addr)
            return

        LOG.info("KeypadLinc %s cmd: increment up", self.addr)
        msg = Msg.OutStandard.direct(self.addr, 0x15, 0x00)

        callback = functools.partial(self.handle_increment, delta=+8)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def increment_down(self, on_done=None):
        """Increment the current level down.

        Levels increment in units of 8 (32 divisions from off to on).

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.
        """
        if not self.is_dimmer:
            LOG.error("KeypadLinc %s switch doesn't support increment down "
                      "command", self.addr)
            return

        LOG.info("KeypadLinc %s cmd: increment down", self.addr)
        msg = Msg.OutStandard.direct(self.addr, 0x16, 0x00)

        callback = functools.partial(self.handle_increment, delta=-8)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def scene(self, is_on, group=0x01, on_done=None):
        """TODO: doc
        """
        LOG.info("KeypadLinc %s %s scene %s", self.addr, group,
                 "on" if is_on else "off")
        assert 1 <= group <= 8

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
        callback = on_done if is_on else None
        msg_handler = handler.StandardCmd(msg, self.handle_scene, callback)
        self.send(msg, msg_handler)

        # Scene triggering will not turn the device off (no idea why), so we
        # have to send an explicit off command to do that.  If this is None,
        # we're triggering a scene and so should bypass the normal
        # handle_broadcast logic to take this case into account.  Note that
        # if we sent and off command either before or after the ACK of the
        # command above, it doesn't work - we have to wait until the
        # broadcast msg is finished.
        if not is_on:
            self.broadcast_done = functools.partial(self.off, group=group,
                                                    on_done=on_done)

    #-----------------------------------------------------------------------
    def set_button_led(self, group, is_on, on_done=None):
        """TODO: doc
        """
        on_done = util.make_callback(on_done)
        LOG.info("KeypadLinc setting LED %s to %s", group, is_on)

        if group < 1 or group > 8:
            LOG.error("KeypadLinc group %s out of range [1,8]", group)
            on_done(False, "Invalid group", None)
            return

        # New LED bit flags to send.  Either set the bit or clear it
        # depending on the input flag.
        led_bits = util.bit_set(self._led_bits, group - 1, is_on)

        # Extended message data - see Insteon dev guide p156.  NOTE: guide is
        # wrong - it says send group, 0x09, 0x01/0x00 to turn that group
        # on/off but that doesn't work.  Must send group 0x01 and the full
        # LED bit mask to adjust the lights.
        data = bytes([
            0x01,   # D1 only group 0x01 works
            0x09,   # D2 set LED state for groups
            led_bits,  # D3 all 8 LED flags.
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_led_ack, group=group,
                                     is_on=is_on, led_bits=led_bits)
        msg_handler = handler.StandardCmd(msg, callback, on_done)

        # Send the message to the PLM modem for protocol.
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_backlight(self, level, on_done=None):
        """TODO: doc

        NOTE: default factory backlight == 0x1f
        """
        LOG.info("KeypadLinc %s setting backlight to %s", self.label, level)

        # Bound to 0x11 <= level <= 0xff per page 157 of insteon dev guide.
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
        msg_handler = handler.StandardCmd(msg, self.handle_backlight,
                                          on_done)

        # Send the message to the PLM modem for protocol.
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_on_level(self, level, on_done=None):
        """TODO: doc

        NOTE: default factory backlight == 0x1f
        """
        if not self.is_dimmer:
            LOG.error("KeypadLinc %s switch doesn't support setting on level",
                      self.addr)
            return

        LOG.info("KeypadLinc %s setting on level to %s", self.label, level)

        # Extended message data - see Insteon dev guide p156.
        data = bytes([
            0x01,   # D1 must be group 0x01
            0x06,   # D2 set on level when button is pressed
            level,  # D3 brightness level
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when
        # the command is ACK'ed.
        msg_handler = handler.StandardCmd(msg, self.handle_on_level,
                                          on_done)

        # Send the message to the PLM modem for protocol.
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_flags(self, on_done, **kwargs):
        """TODO: doc
        valid kwargs:
           backlight: 0x11-0xff (factory default 0x1f)
        """
        LOG.info("KeypadLinc %s cmd: set flags", self.label)

        # Check the input flags to make sure only ones we can understand were
        # passed in.
        flags = set(["backlight", "on_level"])
        unknown = set(kwargs.keys()).difference(flags)
        if unknown:
            raise Exception("Unknown KeypadLinc flags input: %s.\n Valid "
                            "flags are: %s" % unknown, flags)

        seq = CommandSeq(self.protocol, "KeypadLinc set_flags complete",
                         on_done)

        if "backlink" in kwargs:
            backlight = util.input_byte(kwargs, "backlight")
            seq.add(self.set_backlight, backlight)

        if "on_level" in kwargs:
            on_level = util.input_byte(kwargs, "on_level")
            seq.add(self.set_on_level, on_level)

        seq.run()

    #-----------------------------------------------------------------------
    def handle_backlight(self, msg, on_done):
        """TODO: doc
        """
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            on_done(True, "Backlight level updated", None)
        else:
            on_done(False, "Backlight level failed", None)

    #-----------------------------------------------------------------------
    def handle_on_level(self, msg, on_done):
        """TODO: doc
        """
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            on_done(True, "Button on level updated", None)
        else:
            on_done(False, "Button on level failed", None)

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        """Handle replies to the refresh command.

        The refresh command reply will contain the current device group 1
        state in cmd2 and this updates the device with that value.

        Args:
          msg:  (message.InpStandard) The refresh message reply.  The current
                device state is in the msg.cmd2 field.
        """
        # NOTE: This is called by the handler.DeviceRefresh class when the
        # refresh message send by Base.refresh is ACK'ed.
        LOG.ui("KeypadLinc %s refresh at level %s", self.addr, msg.cmd2)

        # Current group 1 level is stored in cmd2 so update our level to
        # match.
        self._set_level(1, msg.cmd2)

    #-----------------------------------------------------------------------
    def handle_led_ack(self, msg, on_done, group, is_on, led_bits):
        """TODO: doc
        """
        # If this it the ACK we're expecting, update the internal state and
        # emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc LED %s group %s ACK: %s", self.addr, group,
                      msg)

            # Update the LED bit for the updated group.
            self._led_bits = led_bits
            LOG.ui("KeypadLinc %s LED's changed to %s", self.addr,
                   "{:08b}".format(self._led_bits))

            # Change the level and emit the active signal.
            self._set_level(group, 0xff if is_on else 0x00)

            msg = "KeypadLinc %s LED updated to %s" % (self.addr, is_on)
            on_done(True, msg, is_on)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc LED %s NAK error: %s, Message: %s",
                      self.addr, msg.nak_str(), msg)
            on_done(False, "KeypadLinc %s LED update failed. " + msg.nak_str(),
                    None)

    #-----------------------------------------------------------------------
    def handle_led_refresh(self, msg):
        """TODO: doc
        """
        led_bits = msg.cmd2

        # Current the led speed is stored in cmd2 so update our speed to
        # match.
        LOG.ui("KeypadLinc %s setting LED bits %s", self.addr,
               "{:08b}".format(led_bits))

        # Loop over the bits and emit a signal for any that have been
        # changed.
        for i in range(8):
            is_on = util.bit_get(led_bits, i)
            was_on = util.bit_get(self._led_bits, i)

            LOG.debug("Btn %d old: %d new %d", i + 1, is_on, was_on)
            if is_on != was_on:
                self._set_level(i + 1, 0xff if is_on else 0x00)

        self._led_bits = led_bits

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        """Handle broadcast messages from this device.

        The broadcast message from a device is sent when the device is
        triggered.  The message has the group ID in it.  We'll update the
        device state and look up the group in the all link database.  For
        each device that is in the group (as a reponsder), we'll call
        handle_group_cmd() on that device to trigger it.  This way all the
        devices in the group are updated to the correct values when we see
        the broadcast message.

        Args:
          msg:   (InptStandard) Broadcast message from the device.
        """
        # Non-group 1 messages are for the scene buttons on keypadlinc.
        # Treat those the same as the remote control does.  They don't have
        # levels to find/set but have similar messages to the dimmer load.

        # ACK of the broadcast - ignore this.  Unless we sent a simulated off
        # scene in which case run the broadcast done handler.  This is a
        # weird special case - see scene() for details.
        if cmd == 0x06:
            LOG.info("KeypadLinc %s broadcast ACK grp: %s", self.addr,
                     msg.group)
            if self.broadcast_done:
                self.broadcast_done()
            self.broadcast_done = None
            return

        # On/off commands.  How do we tell the level?  It's not in the
        # message anywhere.
        elif on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)
            LOG.info("KeypadLinc %s broadcast grp: %s on: %s mode: %s",
                     self.addr, msg.group, is_on, mode)

            if is_on:
                self._set_level(msg.group, 0xff, mode)

            # If broadcast_done is active, this is a generated broadcast and
            # we need to manually turn the device off so don't update it's
            # state until that occurs.
            elif not self.broadcast_done:
                # Notify others that the button was pressed.
                self._set_level(msg.group, 0x00, mode)

        # Starting or stopping manual increment (cmd2 0x00=up, 0x01=down)
        elif on_off.Manual.is_valid(msg.cmd1):
            manual = on_off.Manual.decode(msg.cmd1, msg.cmd2)
            LOG.info("KeypadLinc %s manual change %s", self.addr, manual)

            self.signal_manual.emit(self, msg.group, manual)

            # Non-group 1 buttons don't change state in manual mode. (found
            # through experiments)
            if msg.group == 1:
                # Switches change state when the switch is held.
                if not is_dimmer:
                    if manual == on_off.Manual.UP:
                        self._set_level(0xff, on_off.Mode.MANUAL)
                    elif manual == on_off.Manual.DOWN:
                        self._set_is_on(0x00, on_off.Mode.MANUAL)

                # Ping the device to get the dimmer states - we don't know
                # what the keypadlinc things the state is - could be on or
                # off.  Doing a dim down for a long time puts all the other
                # devices "off" but the keypadlinc can still think that it's
                # on.  So we have to do a refresh to find out.
                elif manual == on_off.Manual.STOP:
                    self.refresh()

        # Call the base class handler.  This will find all the devices we're
        # the controller of for this group and call their handle_group_cmd()
        # methods to update their states since they will have seen the group
        # broadcast and updated (without sending anything out).
        Base.handle_broadcast(self, msg)

    #-----------------------------------------------------------------------
    def handle_ack(self, msg, on_done):
        """Callback for standard commanded messages to group 1.

        This callback is run when we get a reply back from one of our
        commands to the device for changing the group 1 load.  If the command
        was ACK'ed, we know it worked so we'll update the internal state of
        the device and emit the signals to notify others of the state change.

        Args:
          msg:  (message.InpStandard) The reply message from the device.
                The on/off level will be in the cmd2 field.
        """
        # If this it the ACK we're expecting, update the internal state and
        # emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)
            _is_on, mode = on_off.Mode.decode(msg.cmd1)
            self._set_level(1, msg.cmd2, mode)
            on_done(True, "KeypadLinc state updated to %s" % self._level,
                    msg.cmd2)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc %s NAK error: %s", self.addr, msg)
            on_done(False, "KeypadLinc state update failed", None)

    #-----------------------------------------------------------------------
    def handle_scene(self, msg, on_done):
        """Callback for scene simulation commanded messages.

        This callback is run when we get a reply back from triggering a scene
        on the device.  If the command was ACK'ed, we know it worked.  The
        device will then send out standard broadcast messages which will
        trigger other updates for the scene devices.

        Args:
          msg:  (message.InpStandard) The reply message from the device.
        """
        # If this it the ACK we're expecting, update the internal state and
        # emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)
            on_done(True, "Scene triggered", None)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc %s NAK error: %s", self.addr, msg)
            on_done(False, "Scene trigger failed failed", None)

    #-----------------------------------------------------------------------
    def handle_increment(self, msg, on_done, delta):
        """TODO: doc
        """
        # If this it the ACK we're expecting, update the internal state and
        # emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)
            # Add the delta and bound at [0, 255]
            level = min(self._level + delta, 255)
            level = max(level, 0)
            self._set_level(1, level)

            s = "KeypadLinc %s state updated to %s" % (self.addr, self._level)
            on_done(True, s, msg.cmd2)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc %s NAK error: %s", self.addr, msg)
            on_done(False, "KeypadLinc %s state update failed", None)

    #-----------------------------------------------------------------------
    def handle_group_cmd(self, addr, msg):
        """Respond to a group command for this device.

        This is called when this device is a responder to a scene.  The
        device should look up the responder entry for the group in it's all
        link database and update it's state accordingly.

        Args:
          addr:  (Address) The device that sent the message.  This is the
                 controller in the scene.
          msg:   (message.InpStandard) The broadcast message that was sent.
                 Use msg.group to find the scene group that was broadcast.
        """
        group = msg.group
        cmd1 = msg.cmd1

        # Make sure we're really a responder to this message.  This shouldn't
        # ever occur.
        entry = self.db.find(addr, group, is_controller=False)
        if not entry:
            LOG.error("KeypadLinc %s has no group %s entry from %s", self.addr,
                      group, addr)
            return

        # Handle on/off codes
        if on_off.Mode.is_valid(cmd1):
            is_on, mode = on_off.Mode.decode(cmd1)
            level = 0xff if is_on else 0x00
            if self.is_dimmer and is_on and group == 1:
                level = entry.data[0]

            self._set_level(group, level, mode)

        # Increment up (32 steps)
        elif cmd1 == 0x15:
            assert group == 0x01
            self._set_level(group, min(0xff, self._level + 8))

        # Increment down
        elif cmd1 == 0x16:
            assert group == 0x01
            self._set_level(group, max(0x00, self._level - 8))

        # Starting/stopping manual increment (cmd2 0x00=up, 0x01=down)
        elif on_off.Manual.is_valid(msg.cmd1):
            manual = on_off.Manual.decode(msg.cmd1, msg.cmd2)
            self.signal_manual.emit(self, group, manual)

            # Ping the light to get the new level
            if manual == on_off.Manual.STOP:
                self.refresh()

        else:
            LOG.warning("KeypadLinc %s unknown cmd %#04x", self.addr, cmd1)

    #-----------------------------------------------------------------------
    def _set_level(self, group, level, mode=on_off.Mode.NORMAL):
        """Set the device group 1 level state.

        This will change the internal state and emit the state changed
        signals.

        Args:
          group:   (int) group to modify
          level:   (int) 0x00 for off, 0xff for 100%.
        """
        LOG.info("Setting device %s grp=%s on=%s %s", self.label, group,
                 level, mode)
        if group == 0x01:
            self._level = level

        self._led_bits = util.bit_set(self._led_bits, group - 1,
                                      1 if level else 0)

        self.signal_active.emit(self, group, level, mode)

    #-----------------------------------------------------------------------
