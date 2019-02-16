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
    """Insteon KeypadLinc dimmer/switch device.

    This class can be used to model a 6 or 8 button KeypadLinc with dimming
    or non-dimming functionality.  The buttons are numbered 1...8.  In the 6
    button, model, the top and bottom buttons are combined (so buttons 2 and
    7 are unused).  If the load is detached (meaning button 1 is not
    controlling the load), then a virtual button 9 is used to control the
    load.

    If a button is not controlling the load then it's on/off state only
    relates to whether or not the button LED is on or off.  For example,
    setting button group 3 to on just turns the LED on.  In many cases, a
    scene command to button 3 is what you want (to simulate pressing the
    button).

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).  Supported signals are:

    - signal_level_changed( Device, int level, on_off.Mode mode ): Sent
      whenever the dimmer is turned on or off or changes level.  The level
      field will be in the range 0-255.  For an on/off switch, this will only
      emit 0 or 255.

    - signal_manual( Device, on_off.Manual mode ): Sent when the device
      starts or stops manual mode (when a button is held down or released).
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
        self.signal_level_changed = Signal()

        # Manual mode start up, down, off
        # API: func(Device, int group, on_off.Manual mode)
        self.signal_manual = Signal()

        # Remote (mqtt) commands mapped to methods calls.  Add to the base
        # class defined commands.
        self.cmd_map.update({
            'on' : self.on,
            'off' : self.off,
            'set' : self.set,
            'scene' : self.scene,
            'set_flags' : self.set_flags,
            'set_button_led' : self.set_button_led,
            'set_button_signal' : self.set_button_signal,
            'set_led_off_mask' : self.set_led_off_mask,
            'set_led_follow_mask' : self.set_led_follow_mask,
            'set_load_attached' : self.set_load_attached,
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

        # 8 bits representing the buttons on the keypad.  Bit0=button1, ...,
        # Bit7=button8.  If a bit is set, then the button will no longer
        # automatically 'toggle', it will only send a 'on' command.
        self._non_toggle = 0x00

        # A bitmask representing what signal is sent when a button is pressed
        # and it is a non-toggle button.  A value of 0 means 'off' will be
        # sent.  A value of 1 means 'on' will be sent.  Bit0=button1, ...,
        # bit7=button8.
        self._press_signal = 0x00

        # Button 1 level (0-255)
        self._level = 0

        # the group the load is attached to (either 1 or 9).
        self._load_group = 1

    #-----------------------------------------------------------------------
    def pair(self, on_done=None):
        """Pair the device with the modem.

        This only needs to be called one time.  It will set the device as a
        controller and the modem as a responder so the modem will see group
        broadcasts and report them to us.

        The device must already be a responder to the modem (push set on the
        modem, then set on the device) so we can update it's database.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
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
        for group in range(1, 10):
            seq.add(self.db_add_ctrl_of, group, self.modem.addr, group,
                    refresh=False)

        # Also add the modem as a controller for the buttons - this lets the
        # modem issue simulated scene commands to those buttons.
        for group in range(1, 10):
            seq.add(self.db_add_resp_of, group, self.modem.addr, group,
                    refresh=False)

        # Finally start the sequence running.  This will return so the
        # network event loop can process everything and the on_done callbacks
        # will chain everything together.
        seq.run()

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
        # Send a 0x19 0x01 command to get the LED light on/off flags.
        LOG.info("KeypadLinc %s cmd: keypad status refresh", self.addr)

        seq = CommandSeq(self.protocol, "Refresh complete", on_done)

        # This sends a refresh ping which will respond w/ the LED bit flags
        # (1-8) and current database delta field.  Pass skip_db here - we'll
        # let the dimmer refresh handler above take care of getting the
        # database updated.  Otherwise this handler and the one created in
        # the dimmer refresh would download the database twice.
        #TODO: can we move this to 'handle_refresh_state'?
        #msg = Msg.OutStandard.direct(self.addr, 0x19, 0x01)
        #msg_handler = handler.DeviceRefresh(self, self.handle_refresh_led,
        #                                    force=False, num_retry=3,
        #                                    skip_db=True)
        #seq.add_msg(msg, msg_handler)

        # get the group the load is attached to
        msg = Msg.OutStandard.direct(self.addr, 0x1f, 0x05)
        msg_handler = handler.DeviceRefresh(self,
                                            self.handle_refresh_load_state,
                                            force=False, num_retry=3,
                                            skip_db=True)
        seq.add_msg(msg, msg_handler)

        # get the state of which buttons 'toggle' and the signal they emit.
        # since the values we are interested in will be returned regardless
        # of the group number we use, we just use group 1.
        data = bytes([0x01] + [0x00] * 13)
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)
        msg_handler = handler.ExtendedCmdResponse(msg,
                                                  self.handle_refresh_state,
                                                  num_retry=3)
        seq.add_msg(msg, msg_handler)

        # If we get the LED state correctly, then have the base also get it's
        # state and update the database if necessary.  This also calls
        # handle_refresh to set the load group level.
        seq.add(Base.refresh, self, force)

        seq.run()

    #-----------------------------------------------------------------------
    def on(self, group=None, level=0xff, mode=on_off.Mode.NORMAL,
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
          group (int):  The group to send the command to.  Set to None to
                        indicate the load, otherwise whis must be in the
                        range [1,8].
          level (int):  If non zero, turn the device on.  Should be in the
                range 0 to 255.  For non-dimmer groups, it will only look at
                level=0 or level>0.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("KeypadLinc %s cmd: on %s", self.addr, level)

        if group is None:
            group = self._load_group

        assert 1 <= group <= 9
        assert 0 <= level <= 0xff
        assert isinstance(mode, on_off.Mode)

        # Non-load buttons are turned on/off via the LED command.
        if group != self._load_group:
            self.set_button_led(group, True, on_done)

        # Group 1 uses a direct command to set the level.
        else:
            # For switches, on is always full level.
            level = level if self.is_dimmer else 0xff

            # Send the correct on code.
            cmd1 = on_off.Mode.encode(True, mode)
            msg = Msg.OutStandard.direct(self.addr, cmd1, level)

            # Use the standard command handler which will notify us when the
            # command is ACK'ed.
            msg_handler = handler.StandardCmd(msg, self.handle_set_load,
                                              on_done)
            self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def off(self, group=None, mode=on_off.Mode.NORMAL, on_done=None):
        """Turn the device off.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group (int):  The group to send the command to.  Set to None to
                        indicate the load, otherwise whis must be in the
                        range [1,8].
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("KeypadLinc %s cmd: off", self.addr)

        if group is None:
            group = self._load_group

        assert 1 <= group <= 9
        assert isinstance(mode, on_off.Mode)

        # Non-load buttons are turned on/off via the LED command.
        if group != self._load_group:
            self.set_button_led(group, False, on_done)

        # Group 1 uses a direct command to set the level.
        else:
            # Send an off or instant off command.
            cmd1 = on_off.Mode.encode(True, mode)
            msg = Msg.OutStandard.direct(self.addr, cmd1, 0x00)

            # Use the standard command handler which will notify us when the
            # command is ACK'ed.
            msg_handler = handler.StandardCmd(msg, self.handle_set_load,
                                              on_done)
            self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set(self, level, group=None, mode=on_off.Mode.NORMAL, on_done=None):
        """Turn the device on or off.  Level zero will be off.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          level (int):  If non zero, turn the device on.  Should be in the
                range 0 to 255.  For non-dimmer groups, it will only look at
                level=0 or level>0.
          group (int):  The group to send the command to.  Set to None to
                        indicate the load, otherwise whis must be in the
                        range [1,8].
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        if level:
            self.on(group, level, mode, on_done)
        else:
            self.off(group, mode, on_done)

    #-----------------------------------------------------------------------
    def scene(self, is_on, group=None, on_done=None):
        """Trigger a scene on the device.

        Triggering a scene is the same as simulating a button press on the
        device.  It will change the state of the device and notify responders
        that are linked ot the device to be updated.

        Args:
          is_on (bool):  True for an on command, False for an off command.
          group (int):  The group on the device to simulate.  This must be in
                the range [1,8].
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        if group is None:
            group = self._load_group

        LOG.info("KeypadLinc %s %s scene %s", self.addr, group,
                 "on" if is_on else "off")
        assert 1 <= group <= 9

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
    def increment_up(self, on_done=None):
        """Increment the current level up.

        Levels increment in units of 8 (32 divisions from off to on).

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
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

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
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
    def set_load_attached(self, is_attached, on_done=None):
        """Attach/detach the load from group 1

        If the load is detached, tehn it is placed into and controlled as
        group 9.

        Args:
          is_attached (bool):  If True, then the load will be attached, a
                               value of False will detach the load from the
                               button.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        on_done = util.make_callback(on_done)
        LOG.info("KeypadLinc setting load_attached to %s", is_attached)

        load_group = 9
        cmd = 0x1b
        if is_attached:
            load_group = 1
            cmd = 0x1a

        # The dev KeypadLinc guide says this should be a Standard message,
        # but, it should actually be Extended.
        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd, [0x00] * 14)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_load_attach,
                                     load_group=load_group)
        msg_handler = handler.StandardCmd(msg, callback, on_done)

        # Send the message to the PLM modem for protocol.
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_button_led(self, group, is_on, on_done=None):
        """Set a button LED on or off.

        This changes the level of the LED state of a button.  NOTE: This does
        NOT simulate a button press on the device - it just changes the state
        of the device.  It will not trigger any responders that are linked to
        this device.  To simulate a button press, call the scene() method.

        Args:
          group (int):  The group to send the command to.  This must be in the
                range [1,8].
          is_on (bool):  True to turn it on, False to turn it off.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
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
        callback = functools.partial(self.handle_button_led, group=group,
                                     is_on=is_on, led_bits=led_bits)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

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
        LOG.info("KeypadLinc %s setting backlight to %s", self.label, level)

        # Bound to 0x11 <= level <= 0x7f per page 157 of insteon dev guide.
        # allow a value of '0x00' to disable the backlight.
        if level:
            level = max(0x11, min(level, 0x7f))

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
    def set_button_signal(self, group, signal, on_done=None):
        """Set whether or not a button toggles.

        Args:
           group (int):  The group number to modify
           signal (bool):  If True, then pressing the specified group will
                       send the 'on' signal.  If False, then it will emit the
                       'off' signal.  If None, then pressing the group will
                       toggle the state (this is the default behaviour).
        """
        on_done = util.make_callback(on_done)

        msg = "toggle"
        if signal is not None:
            msg = "emit %s when pressed" % ("'on'" if signal else "'off'")
        LOG.info("setting button %s to %s", group, msg)

        if group < 1 or group > 8:
            LOG.error("KeypadLinc group %s out of range [1,8]", group)
            on_done(False, "Invalid group", None)
            return

        seq = CommandSeq(self.protocol, "KeypadLinc set_button_signal done",
                         on_done)

        toggle_off = False
        if signal is not None:
            toggle_off = True
            LOG.debug("group %s - disable toggle", group)

            # First specify what signal to send (if non-toggle enabled)
            signal_bits = util.bit_set(self._press_signal, group - 1, signal)
            LOG.debug("signal_bits: %s", "{:08b}".format(signal_bits))
            data = bytes([
                0x01,   # D1 must be group 0x01
                0x0b,   # D2 set non-toggle signal
                signal_bits,  # D3 non-toggle signal
                ] + [0x00] * 11)

            msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

            # Use the standard command handler which will notify us when the
            # command is ACK'ed.
            callback = functools.partial(self.handle_button_signal,
                                         group=group, signal_bits=signal_bits)
            msg_handler = handler.StandardCmd(msg, callback, on_done)

            seq.add_msg(msg, msg_handler)

        # next set the non-toggle flag
        toggle_bits = util.bit_set(self._non_toggle, group - 1, toggle_off)
        LOG.debug("toggle_bits: %s", "{:08b}".format(toggle_bits))
        data = bytes([
            0x01,   # D1 must be group 0x01
            0x08,   # D2 set non-toggle enabled
            toggle_bits,  # D3 non-toggle enabled
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_button_signal,
                                     group=group, toggle_bits=toggle_bits)
        msg_handler = handler.StandardCmd(msg, callback, on_done)

        seq.add_msg(msg, msg_handler)
        seq.run()

    #-----------------------------------------------------------------------
    def set_led_follow_mask(self, group, mask, on_done=None):
        """Set the LED follow mask.

        The LED follow mask is a bitmask defined for each group (button),
        such that a value of 1 means that the associated button state will
        follow the state of this button.

        Args:
          group (int): The group number to modify
          mask (int):  A Value in the range of 0x00 to 0x08.  This is
                       a bitmask, where  each bit represents a button and a
                       value of one means that the associated button's LED
                       will follow the state of the button associated with
                       'group'.
        """
        on_done = util.make_callback(on_done)
        LOG.info("KeypadLinc setting button %s state to lead: %s",
                 group, "{:08b}".format(mask))

        if group < 1 or group > 8:
            LOG.error("KeypadLinc group %s out of range [1,8]", group)
            on_done(False, "Invalid group", None)
            return

        data = bytes([
            group,  # D1 must be group
            0x02,   # D2 set LED follow mask
            mask,   # D3 bitmask value
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_follow_mask, group=group,
                                     bitmask=mask)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_led_off_mask(self, group, mask, on_done=None):
        """Set the LED off mask.

        The LED off mask is a bitmask defined for each group (button), such
        that a value of 1 means that the associated button will toggle to
        off when this button is pressed.

        Args:
          group (int): The group number to modify
          mask (int):  A Value in the range of 0x00 to 0x08.  This is
                       a bitmask, where  each bit represents a button and a
                       value of one means that the associated button's LED
                       will turn off when the button associated with
                       'group' is pressed.
        """
        on_done = util.make_callback(on_done)
        LOG.info("KeypadLinc setting button %s state to turn off: %s",
                 group, "{:08b}".format(mask))

        if group < 1 or group > 8:
            LOG.error("KeypadLinc group %s out of range [1,8]", group)
            on_done(False, "Invalid group", None)
            return

        data = bytes([
            group,  # D1 must be group
            0x03,   # D2 set LED off mask
            mask,   # D3 bitmask value
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_off_mask, group=group,
                                     bitmask=mask)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_on_level(self, level, on_done=None):
        """Set the device default on level.

        This changes the dimmer level the device will go to when the on
        button is pressed.  This can be very useful because a double-tap
        (fast-on) will the turn the device to full brightness if needed.

        Args:
          level (int):  The default on level in the range [0,255]
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
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

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        msg_handler = handler.StandardCmd(msg, self.handle_on_level, on_done)

        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_flags(self, on_done, **kwargs):
        """Set internal device flags.

        This command is used to change internal device flags and states.
        Valid inputs are:

        - backlight=level:  Change the backlight LED level (0-255).  See
          set_backlight() for details.

        - on_level=level: Change the default device on level (0-255) See
          set_on_level for details.

        Args:
          kwargs: Key=value pairs of the flags to change.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("KeypadLinc %s cmd: set flags", self.label)

        # Check the input flags to make sure only ones we can understand were
        # passed in.
        flags = set(["backlight", "button_signal", "follow_mask", "group",
                     "load_attached", "off_mask", "on_level"])
        unknown = set(kwargs.keys()).difference(flags)
        if unknown:
            raise Exception("Unknown KeypadLinc flags input: %s.\n Valid "
                            "flags are: %s" % (unknown, flags))

        # Start a command sequence so we can call the flag methods in series.
        seq = CommandSeq(self.protocol, "KeypadLinc set_flags complete",
                         on_done)

        group = util.input_integer(kwargs, "group")

        if "backlight" in kwargs:
            backlight = util.input_byte(kwargs, "backlight")
            seq.add(self.set_backlight, backlight)

        if "button_signal" in kwargs:
            if group is None:
                raise Exception("Must specify 'group=<group_number>' when "
                                "setting the 'button_signal' flag")
            signal = util.input_bool(kwargs, "button_signal")

            seq.add(self.set_button_signal, group, signal)

        if "follow_mask" in kwargs:
            if group is None:
                raise Exception("Must specify 'group=<group_number>' when "
                                "setting the 'follow_mask' flag")
            follow_mask = util.input_byte(kwargs, "follow_mask")

            seq.add(self.set_led_follow_mask, group, follow_mask)

        if "load_attached" in kwargs:
            load_attached = util.input_bool(kwargs, "load_attached")
            seq.add(self.set_load_attached, load_attached)

        if "off_mask" in kwargs:
            if group is None:
                raise Exception("Must specify 'group=<group_number>' when "
                                "setting the 'off_mask' flag")
            off_mask = util.input_byte(kwargs, "off_mask")

            seq.add(self.set_led_off_mask, group, off_mask)

        if "on_level" in kwargs:
            on_level = util.input_byte(kwargs, "on_level")
            seq.add(self.set_on_level, on_level)

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
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            on_done(True, "Backlight level updated", None)
        else:
            on_done(False, "Backlight level failed", None)

    #-----------------------------------------------------------------------
    def handle_on_level(self, msg, on_done):
        """Callback for handling set_on_level() responses.

        This is called when we get a response to the set_on_level() command.
        We don't need to do anything - just call the on_done callback with
        the status.

        Args:
          msg (InpStandard):  The response message from the command.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            on_done(True, "Button on level updated", None)
        else:
            on_done(False, "Button on level failed", None)

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        """Handle replies to the refresh command.

        The refresh command reply will contain the current device load group
        state in cmd2 and this updates the device with that value.

        Args:
          msg:  (message.InpStandard) The refresh message reply.  The current
                device state is in the msg.cmd2 field.
        """
        # NOTE: This is called by the handler.DeviceRefresh class when the
        # refresh message send by Base.refresh is ACK'ed.
        LOG.ui("KeypadLinc %s refresh at level %s", self.addr, msg.cmd2)

        # Current load group level is stored in cmd2 so update our level to
        # match.
        self._set_level(self._load_group, msg.cmd2)

    #-----------------------------------------------------------------------
    def handle_button_led(self, msg, on_done, group, is_on, led_bits):
        """Handle replies to setting the button LED state.

        This is called when we change one of the LED button states.  Since
        all 8 buttons are stored in a single integer, we're not told what the
        resulting state is by the reply message.  So the message sender (see
        set_button_led()) passes that to us as part of the callback to make
        processing simpler.

        Args:
          msg (InpStandard):  The message reply.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
          group (int):  The group to send the command to.  This must be in the
                range [1,8].
          is_on (bool):  True for an on command, False for an off command.
          led_bits (int): The LED bits that were set to the device.  If the
                   msg is an ACK, we'll set our state to this value.
        """
        # If this is the ACK we're expecting, update the internal state and
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
    def handle_button_signal(self, msg, on_done, group, toggle_bits=None,
                             signal_bits=None):
        """Handle replies to setting the button signal.

        This is called when we change what signal a button sends when it is
        pressed.

        Args:
          msg (InpStandard):  The message reply.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
          group (int):  The group to send the command to.  This must be in the
                range [1,8].
          toggle_bits (int): The button bits that determine if the button
                             toggles or not.  If the message is an ACK, then
                             we store the state.
          signal_bits (int):  The button bits that determine what signal is
                              emitted if the button does not toggle.  If the
                              mesaage is an ACK, then we store the state.
        """
        # If this is the ACK we're expecting, update the internal state and
        # emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc toggle %s group %s ACK: %s", self.addr,
                      group, msg)

            if toggle_bits is not None:
                # update with the new toggle bit mask
                self._non_toggle = toggle_bits

                LOG.ui("KeypadLinc %s non_toggle changed to %s", self.addr,
                       "{:08b}".format(self._non_toggle))

            if signal_bits is not None:
                # update with the new signal bit mask
                self._press_signal = signal_bits

                LOG.ui("KeypadLinc %s press_signal changed to %s", self.addr,
                       "{:08b}".format(self._press_signal))

            msg = "KeypadLinc %s toggle flags updated" % self.addr
            on_done(True, msg, None)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc toggle %s NAK error: %s", self.addr, msg)
            msg = "KeypadLinc %s toggle update failed" % self.addr
            on_done(False, msg, None)

    #-----------------------------------------------------------------------
    def handle_follow_mask(self, msg, group, bitmask, on_done):
        """Callback for changing the load attachment.

        Args:
          msg (InpStandard):  The reply message from the device.
          group (int):  The group to send the command to.  This must be in the
                range [1,8].
          bitmask (int):  The bitmask describing which groups will follow
                          the state of this group.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # If this it the ACK we're expecting, update the internal state and
        # emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)
            on_done(True, "Group: %s LED leads %s" %
                    (group, "{:08b}".format(bitmask)), None)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc %s NAK error: %s", self.addr, msg)
            on_done(False, "Changing follow mask failed", None)

    #-----------------------------------------------------------------------
    def handle_off_mask(self, msg, group, bitmask, on_done):
        """Callback for changing the load attachment.

        Args:
          msg (InpStandard):  The reply message from the device.
          group (int):  The group to send the command to.  This must be in the
                range [1,8].
          bitmask (int):  The bitmask describing which groups will turn off
                          when this group is activated.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # If this it the ACK we're expecting, update the internal state and
        # emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)
            on_done(True, "Group: %s LED turns off %s" %
                    (group, "{:08b}".format(bitmask)), None)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc %s NAK error: %s", self.addr, msg)
            on_done(False, "Changing follow mask failed", None)

    #-----------------------------------------------------------------------
    def handle_refresh_load_state(self, msg):
        """Callback for determining the load group.

        This is called during the refresh command. It's only called if we
        get an ACK so we don't need to check that part of the message.

        Args:
          msg (InpStandard):  The message reply.
        """
        LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)

        keypad_bits = msg.cmd2
        detach_load = util.bit_get(keypad_bits, 5)

        if detach_load:
            LOG.ui("KeypadLinc %s load detached from buttons and "
                   "assigned to group 9", self.addr)
            self._load_group = 9
        else:
            LOG.ui("KeypadLinc %s load attached to button 1 and "
                   "assigned to group 1", self.addr)
            self._load_group = 1

    #-----------------------------------------------------------------------
    def handle_refresh_led(self, msg):
        """Callback for handling getting the LED button states.

        This is called during the refresh command when we get back the
        current LED button state bits in the message.  It's only called if we
        get an ACK so we don't need to check that part of the message.

        If any of the current LED states are different than what we have now,
        a changed signal is emitted.

        Args:
          msg (InpStandard):  The message reply.
        """
        pass
        #TODO: delete this method
        #led_bits = msg.cmd2

        # Currently the led state is stored in cmd2 so update our state to
        # match.
        #LOG.ui("KeypadLinc %s setting LED bits %s", self.addr,
        #       "{:08b}".format(led_bits))

        # Loop over the bits and emit a signal for any that have been
        # changed.
        #for i in range(8):
        #    is_on = util.bit_get(led_bits, i)
        #    was_on = util.bit_get(self._led_bits, i)

        #    LOG.debug("Btn %d old: %d new %d", i + 1, is_on, was_on)
        #    if is_on != was_on:
        #        self._set_level(i + 1, 0xff if is_on else 0x00)

        #self._led_bits = led_bits

    #-----------------------------------------------------------------------
    def handle_refresh_state(self, msg, on_done):
        """Callback for handling getting the button states.

        Args:
          msg (InpExtended):  The message reply.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        #TODO: merge this with 'handle_refresh_led'
        # - needs an updated refresh handler that can accept an extended reply
        LOG.debug("KeypadLinc %s Get button state: %s", self.addr, msg)

        non_toggle_mask = msg.data[9]
        led_bits = msg.data[10]
        signal_mask = msg.data[12]

        LOG.ui("KeypadLinc %s ramp rate: %s", self.addr, msg.data[6])
        LOG.ui("KeypadLinc %s on level: %s", self.addr, msg.data[7])
        LOG.ui("KeypadLinc %s backlight level: %s", self.addr, msg.data[8])

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

        LOG.ui("KeypadLinc %s setting non_toggle_mask %s",
               self.addr, "{:08b}".format(non_toggle_mask))
        self._non_toggle = non_toggle_mask

        LOG.ui("KeypadLinc %s setting signal_mask %s", self.addr,
               "{:08b}".format(signal_mask))
        self._press_signal = signal_mask

        on_done(True, "Refreshed keypad state", None)

    #-----------------------------------------------------------------------
    def handle_load_attach(self, msg, load_group, on_done):
        """Callback for changing the load attachment.

        Args:
          msg (InpExtended): The reply message from the device.
          load_group (int):  The group the load is attached to.
        """
        # If this it the ACK we're expecting, update the internal state and
        # emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)
            self._load_group = load_group
            on_done(True, "Load Group: %s" % load_group, None)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc %s NAK error: %s", self.addr, msg)
            on_done(False, "Changing the load group failed", None)

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
          msg (InpStandard):  Broadcast message from the device.
        """
        # Non-group 1 messages are for the scene buttons on keypadlinc.
        # Treat those the same as the remote control does.  They don't have
        # levels to find/set but have similar messages to the dimmer load.

        # ACK of the broadcast.  Ignore this unless we sent a simulated off
        # scene in which case run the broadcast done handler.  This is a
        # weird special case - see scene() for details.
        if msg.cmd1 == 0x06:
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

            # For an off command, we need to see if broadcast_done is active.
            # This is a generated broadcast and we need to manually turn the
            # device off so don't update it's state until that occurs.
            elif not self.broadcast_done:
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
                if not self.is_dimmer:
                    if manual == on_off.Manual.UP:
                        self._set_level(0xff, on_off.Mode.MANUAL)
                    elif manual == on_off.Manual.DOWN:
                        self._set_level(0x00, on_off.Mode.MANUAL)

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
    def handle_set_load(self, msg, on_done):
        """Callback for standard commanded messages to the load button.

        This callback is run when we get a reply back from one of our
        commands to the device for changing the load (usually group 1).  If
        the command was ACK'ed, we know it worked so we'll update the
        internal state of the device and emit the signals to notify others
        of the state change.

        Args:
          msg:  (message.InpStandard) The reply message from the device.
                The on/off level will be in the cmd2 field.
        """
        # If this is the ACK we're expecting, update the internal state and
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
          msg (message.InpStandard): The reply message from the device.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # Call the callback.  We don't change state here - the device will
        # send a regular broadcast message which will run handle_broadcast
        # which will then update the state.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)
            on_done(True, "Scene triggered", None)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc %s NAK error: %s", self.addr, msg)
            on_done(False, "Scene trigger failed failed", None)

    #-----------------------------------------------------------------------
    def handle_increment(self, msg, on_done, delta):
        """Callback for increment up/down commanded messages.

        This callback is run when we get a reply back from triggering an
        increment up or down on the device.  If the command was ACK'ed, we
        know it worked.

        Args:
          msg (message.InpStandard): The reply message from the device.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
          delta (int):  The amount +/- of level to change by.
        """
        # If this it the ACK we're expecting, update the internal state and
        # emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)

            # Add the delta and bound at [0, 255]
            level = min(self._level + delta, 255)
            level = max(level, 0)
            self._set_level(self._load_group, level)

            s = "KeypadLinc %s state updated to %s" % (self.addr, self._level)
            on_done(True, s, msg.cmd2)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc %s NAK error: %s", self.addr, msg)
            on_done(False, "KeypadLinc %s state update failed", None)

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
            LOG.error("KeypadLinc %s has no group %s entry from %s", self.addr,
                      msg.group, addr)
            return

        # Handle on/off codes
        if on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)

            # For switches, on/off determines the level.  For dimmers, it's
            # set by the responder entry in the database.
            level = 0xff if is_on else 0x00
            if self.is_dimmer and is_on and msg.group == 1:
                level = entry.data[0]

            self._set_level(msg.group, level, mode)

        # Increment up 1 unit which is 8 levels.
        elif msg.cmd1 == 0x15:
            assert msg.group == 0x01
            self._set_level(msg.group, min(0xff, self._level + 8))

        # Increment down 1 unit which is 8 levels.
        elif msg.cmd1 == 0x16:
            assert msg.group == 0x01
            self._set_level(msg.group, max(0x00, self._level - 8))

        # Starting/stopping manual increment (cmd2 0x00=up, 0x01=down)
        elif on_off.Manual.is_valid(msg.cmd1):
            manual = on_off.Manual.decode(msg.cmd1, msg.cmd2)
            self.signal_manual.emit(self, msg.group, manual)

            # If the button is released, refresh to get the final level in
            # dimming mode since we don't know where the level stopped.
            if manual == on_off.Manual.STOP:
                self.refresh()

        else:
            LOG.warning("KeypadLinc %s unknown cmd %#04x", self.addr,
                        msg.cmd1)

    #-----------------------------------------------------------------------
    def _set_level(self, group, level, mode=on_off.Mode.NORMAL):
        """Update the device level state for a group.

        This will change the internal state and emit the state changed
        signals.  It is called by whenever we're informed that the device has
        changed state.

        Args:
          group (int):  The group number to update [1,8].
          level (int):  The new device level in the range [0,255].  0 is off.
          mode (on_off.Mode): The type of on/off that was triggered (normal,
               fast, etc).
        """
        LOG.info("Setting device %s grp=%s on=%s %s", self.label, group,
                 level, mode)
        if group == self._load_group:
            self._level = level

        # Update the LED bits in the correct slot.
        self._led_bits = util.bit_set(self._led_bits, group - 1,
                                      1 if level else 0)

        self.signal_level_changed.emit(self, group, level, mode)

    #-----------------------------------------------------------------------
