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
from . import Dimmer

LOG = log.get_logger()


#===========================================================================
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

    - signal_level_changed( Device, int level, on_off.Mode mode, str reason):
      Sent whenever the dimmer is turned on or off or changes level.  The
      level field will be in the range 0-255.  For an on/off switch, this
      will only emit 0 or 255.

    - signal_manual( Device, on_off.Manual mode, str reason ): Sent when the
      device starts or stops manual mode (when a button is held down or
      released).
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
        # API: func(Device, int group, int level, on_off.Mode mode, str reason)
        self.signal_level_changed = Signal()

        # Manual mode start up, down, off
        # API: func(Device, int group, on_off.Manual mode, str reason)
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
            'set_load_attached' : self.set_load_attached,
            'set_led_follow_mask' : self.set_led_follow_mask,
            'set_led_off_mask' : self.set_led_off_mask,
            'set_signal_bits' : self.set_signal_bits,
            'set_nontoggle_bits' : self.set_nontoggle_bits,
            })

        if self.is_dimmer:
            self.cmd_map.update({
                'increment_up' : self.increment_up,
                'increment_down' : self.increment_down,
                })

        # Special callback to run when receiving a broadcast clean up.  See
        # scene() for details.
        self.broadcast_done = None
        self.broadcast_reason = ""

        # TODO: these fields need to be stored in the database, updated when
        # changed, read on startup, and updated during a forced refresh or if
        # they don't exist in the database.

        # 8 bits representing the LED's on the device for buttons 1-8.  For
        # buttons 2-8 (8 button keypad) and 3-6 (6 button keypad), these also
        # represent the state of the switch on vs off.  The load controller
        # button (1 on 8 btn and 1,2,7,8 on 6 btn), cannot be controlled by
        # changing the led state - only toggling the load changes the state.
        # Since the non-load buttons have nothing to switch, the led state is
        # the state of the switch.
        self._led_bits = 0x00

        # 1 if the load is attached to the normal first button.  If the load
        # is detached, this will be group 9.
        self._load_group = 1

        # Button 1 level (0-255)
        self._level = 0

        # Backlight on/off.  See set_backlight for details.
        self._backlight = True

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
        # the button presses and state changes.  Group 9 is used when the
        # laod is detached so include that as well.
        for group in range(1, 10):
            seq.add(self.db_add_ctrl_of, group, self.modem.addr, group,
                    refresh=False)

        # Note: originally modem was set as the controller for each button.
        # I don't think that's actually necessary - I think the group 1 link
        # above is enough for the modem to control the device.
        ## Also add the modem as a controller for the buttons - this lets the
        ## modem issue simulated scene commands to those buttons.
        #for group in range(1, 10):
        #    seq.add(self.db_add_resp_of, group, self.modem.addr, group,
        #            refresh=False)

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

        # TODO: change this to 0x2e get extended which reads on mask, off
        # mask, on level, led brightness, non-toggle mask, led bit mask (led
        # on/off), on/off bit mask, etc (see keypadlinc manual)

        #
        # First send a refresh command which get's the state of the LED's by
        # returning a bit flag.  Pass skip_db here - we'll let the second
        # refresh handler below take care of getting the database updated.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x01)
        msg_handler = handler.DeviceRefresh(self, self.handle_refresh_led,
                                            force=False, num_retry=3,
                                            skip_db=True)
        seq.add_msg(msg, msg_handler)

        # Send a refresh command to get the state of the load.  This may or
        # may not match the LED state depending on if detached load is set.
        # This also responds w/ the current database delta field.  The
        # handler checks that against the current value.  If it's different,
        # it will send a database download command to the device to update
        # the database.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x00)
        msg_handler = handler.DeviceRefresh(self, self.handle_refresh, force,
                                            None, num_retry=3)
        seq.add_msg(msg, msg_handler)

        # Update any internal configuration data that we don't know (cats,
        # firmware revisions, etc).  If model number is not known, or force
        # true, run get_model
        self.addRefreshData(seq, force)

        # Run all the commands.
        seq.run()

    #-----------------------------------------------------------------------
    def addRefreshData(self, seq, force=False):
        """Add commands to refresh any internal data required.

        The base class uses this update the device catalog ID's and firmware
        if we don't know what they are.

        This is split out of refresh() so derived classes that override
        refresh can also get this information.

        Args:
          seq (CommandSeq): The command sequence to add the command to.
          force (bool):  If true, will force a refresh of the device database
                even if the delta value matches as well as a re-query of the
                device model information even if it is already known.
        """
        Base.addRefreshData(self, seq, force)

        # TODO: update db.  Only call if needed.

        # Get the state of which buttons toggle and the signal they emit.
        # Since the values we are interested in will be returned regardless
        # of the group number we use, we just use group 1.
        data = bytes([0x01] + [0x00] * 13)
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)
        msg_handler = handler.ExtendedCmdResponse(msg,
                                                  self.handle_refresh_state)
        seq.add_msg(msg, msg_handler)

    #-----------------------------------------------------------------------
    def on(self, group=0, level=0xff, mode=on_off.Mode.NORMAL, reason="",
           on_done=None):
        """Turn the device on.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.  If the input button is controlling the load (group 1
        for an attached load, group 0 for attached or detached), then the
        load will turn on.  Otherwise this command just changes the LED of
        the button.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group (int): The group to send the command to.  If the group is 0,
                it will always be the load (whether it's attached or not).
                Otherwise it must be in the range [1,8] and controls the
                specific button.
          level (int):  If non zero, turn the device on.  Should be in the
                range 0 to 255.  For non-dimmer groups, it will only look at
                level=0 or level>0.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)

        """
        LOG.info("KeypadLinc %s cmd: on grp %s %s", self.addr, group, level)

        # If the group is 0, use the load group.
        group = self._load_group if group == 0 else group

        LOG.debug("load group= %s group= %s", self._load_group, group)

        assert 1 <= group <= 9
        assert 0 <= level <= 0xff
        assert isinstance(mode, on_off.Mode)

        # Non-load buttons are turned on/off via the LED command.
        if group != self._load_group:
            self.set_button_led(group, True, reason, on_done)

        # Load group uses a direct command to set the level.
        else:
            # For switches, on is always full level.
            level = level if self.is_dimmer else 0xff

            # Send the correct on code.
            cmd1 = on_off.Mode.encode(True, mode)
            msg = Msg.OutStandard.direct(self.addr, cmd1, level)

            # Use the standard command handler which will notify us when the
            # command is ACK'ed.
            callback = functools.partial(self.handle_set_load, reason=reason)
            msg_handler = handler.StandardCmd(msg, callback, on_done)
            self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def off(self, group=0, mode=on_off.Mode.NORMAL, reason="", on_done=None):
        """Turn the device off.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.  If the input button is controlling the load (group 1
        for an attached load, group 0 for attached or detached), then the
        load will turn off.  Otherwise this command just changes the LED of
        the button.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group (int): The group to send the command to.  If the group is 0,
                it will always be the load (whether it's attached or not).
                Otherwise it must be in the range [1,8] and controls the
                specific button.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("KeypadLinc %s cmd: off grp %s", self.addr, group)

        # If the group is 0, use the load group.
        group = self._load_group if group == 0 else group

        assert 1 <= group <= 9
        assert isinstance(mode, on_off.Mode)

        # Non-load buttons are turned on/off via the LED command.
        if group != self._load_group:
            self.set_button_led(group, False, reason, on_done)

        # Load group uses a direct command to set the level.
        else:
            # Send an off or instant off command.
            cmd1 = on_off.Mode.encode(False, mode)
            msg = Msg.OutStandard.direct(self.addr, cmd1, 0x00)

            # Use the standard command handler which will notify us when the
            # command is ACK'ed.
            callback = functools.partial(self.handle_set_load, reason=reason)
            msg_handler = handler.StandardCmd(msg, callback, on_done)
            self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set(self, level, group=0, mode=on_off.Mode.NORMAL, reason="",
            on_done=None):
        """Turn the device on or off.  Level zero will be off.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.   If the input button is controlling the load (group 1
        for an attached load, group 0 for attached or detached), then the
        load will change.  Otherwise this command just changes the LED of
        the button.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          level (int):  If non zero, turn the device on.  Should be in the
                range 0 to 255.  For non-dimmer groups, it will only look at
                level=0 or level>0.
          group (int): The group to send the command to.  If the group is 0,
                it will always be the load (whether it's attached or not).
                Otherwise it must be in the range [1,8] and controls the
                specific button.
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
          group (int):  The group on the device to simulate.  This must be in
                the range [1,8].
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
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
    def increment_up(self, reason="", on_done=None):
        """Increment the current level up.

        Levels increment in units of 8 (32 divisions from off to on).

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        if not self.is_dimmer:
            LOG.error("KeypadLinc %s switch doesn't support increment up "
                      "command", self.addr)
            return

        LOG.info("KeypadLinc %s cmd: increment up", self.addr)
        msg = Msg.OutStandard.direct(self.addr, 0x15, 0x00)

        callback = functools.partial(self.handle_increment, delta=+8,
                                     reason=reason)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def increment_down(self, reason="", on_done=None):
        """Increment the current level down.

        Levels increment in units of 8 (32 divisions from off to on).

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        if not self.is_dimmer:
            LOG.error("KeypadLinc %s switch doesn't support increment down "
                      "command", self.addr)
            return

        LOG.info("KeypadLinc %s cmd: increment down", self.addr)
        msg = Msg.OutStandard.direct(self.addr, 0x16, 0x00)

        callback = functools.partial(self.handle_increment, delta=-8,
                                     reason=reason)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

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
            defaults = [0x03, 0x00, group]

        # Responder data is always link dependent.  Since nothing was given,
        # assume the user wants to turn the device on (0xff).
        else:
            data_2 = 0x00
            if self.is_dimmer:
                data_2 = 0x1f
            defaults = [0xff, data_2, group]

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
        ret = [{'data_1': data[0]}, {'data_2': data[1]}, {'group': data[2]}]
        if not is_controller:
            if self.is_dimmer:
                ramp = 0x1f  # default
                if data[1] in Dimmer.ramp_pretty:
                    ramp = Dimmer.ramp_pretty[data[1]]
                on_level = int((data[0] / .255) + .5) / 10
                ret = [{'on_level': on_level},
                       {'ramp_rate': ramp},
                       {'group': data[2]}]
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
        data_1 = None
        if 'data_1' in data:
            data_1 = data['data_1']
        data_2 = None
        if 'data_2' in data:
            data_2 = data['data_2']
        data_3 = None
        if 'data_3' in data:
            data_3 = data['data_3']
        if 'group' in data:
            data_3 = data['group']
        if not is_controller and self.is_dimmer:
            if 'ramp' in data:
                data_2 = 0x1f
                for ramp_key, ramp_value in Dimmer.ramp_pretty:
                    if data['ramp'] >= ramp_value:
                        data_2 = ramp_key
            if 'on_level' in data:
                data_1 = int(data['on_level'] * 2.55 + .5)
        return [data_1, data_2, data_3]

    #-----------------------------------------------------------------------
    def set_load_attached(self, is_attached, on_done=None):
        """Attach or detach the load from group 1

        By default, the load is attached.  In this mode, the first button
        (and group 1 commands) toggle the load and change the button 1 LED
        state.  If the load is set to detached, then group 9 (or sending
        group 0 commands to this object) will control the load and button 1
        acts like any of the other buttons and just changes LED state.

        Args:
          is_attached (bool):  If True, then the load will be attached, a
                      value of False will detach the load from the button.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("KeypadLinc %s setting load_attached to %s", self.addr,
                 is_attached)

        on_done = util.make_callback(on_done)

        # The dev KeypadLinc guide says this should be a Standard message,
        # but, it should actually be Extended.
        cmd = 0x1a if is_attached else 0x1b
        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd, bytes([0x00] * 14))

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_load_attach,
                                     is_attached=is_attached)
        msg_handler = handler.StandardCmd(msg, callback, on_done)

        # Send the message to the PLM modem for protocol.
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_button_led(self, group, is_on, reason="", on_done=None):
        """Set a button LED on or off.

        This changes the level of the LED state of a button.  NOTE: This does
        NOT simulate a button press on the device - it just changes the state
        of the device.  It will not trigger any responders that are linked to
        this device.  To simulate a button press, call the scene() method.

        Button 1 is a special case - if button 1 is controlling the load,
        then it's controlled via regular on and off commands. But - if button
        1 isn't controlling the load, it can't be changed with a direct
        command.  In that case, we need a virtual scene on the model to
        control the button 1 LED.

        Args:
          group (int):  The group to send the command to.  This must be in the
                range [1,8].
          is_on (bool):  True to turn it on, False to turn it off.
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)

        """
        on_done = util.make_callback(on_done)
        reason = reason if reason else on_off.REASON_COMMAND

        LOG.info("KeypadLinc setting LED %s to %s", group, is_on)

        if group < 1 or group > 8:
            LOG.error("KeypadLinc group %s out of range [1,8]", group)
            on_done(False, "Invalid group", None)
            return
        elif group == self._load_group:
            LOG.error("KeypadLinc.set_button_led called for load group %s",
                      group)
            on_done(False, "Invalid group", None)
            return

        # New LED bit flags to send.  Either set the bit or clear it
        # depending on the input flag.
        led_bits = util.bit_set(self._led_bits, group - 1, is_on)

        # Group 1 LED is controlled w/ a separate command from the other LED
        # bits (just another weird Insteon behavior).  The only way to toggle
        # group 1 when the load is detached is to send a simulated scene
        # command from the modem.
        if group == 1:
            # TODO: create virtual modem scene to control group 1 when load
            # is detached.  Need to store that in the device db somehow.

            # There doesn't seem to be anyway to toggle just group 1
            # LED command - the only way I could find to do it is to create a
            # virtual scene on the modem and then trigger that.  This really
            # only applies to detached load cases.
            #modem_scene = 100
            #self.broadcast_reason = reason
            #LOG.info("KeypadLinc %s triggering modem scene %s", self.label,
            #         modem_scene)
            #self.modem.scene(is_on, modem_scene, on_done=on_done)
            pass

        else:
            # Extended message data - see Insteon dev guide p156.  NOTE:
            # guide is wrong - it says send group, 0x09, 0x01/0x00 to turn
            # that group on/off but that doesn't work.  Must send group 0x01
            # and the full LED bit mask to adjust the lights.
            data = bytes([
                0x01,   # D1 only group 0x01 works
                0x09,   # D2 set LED state for groups
                led_bits,  # D3 all 8 LED flags.
                ] + [0x00] * 11)

            msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

            # Use the standard command handler which will notify us when the
            # command is ACK'ed.
            callback = functools.partial(self.handle_button_led, group=group,
                                         is_on=is_on, led_bits=led_bits,
                                         reason=reason)
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

        # If the input level is zero, turn off the backlight.  That's a
        # different command than setting the level.  We also need to keep
        # track of it being off because we need to turn it back on before
        # setting the level if that level is changed in the future.
        if not level:
            self.set_backlight_on(False, on_done)

        # Otherwise use the level changing command.
        else:
            seq = CommandSeq(self.protocol, "Backlight level", on_done)

            # Bound to 0x11 <= level <= 0x7f per page 157 of insteon dev guide.
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
            callback = functools.partial(self.handle_ack,
                                         task="Backlight level")
            msg_handler = handler.StandardCmd(msg, callback, on_done)
            seq.add_msg(msg, msg_handler)

            # If the backlight was off, turn it back on.
            if not self._backlight:
                seq.add(self.set_backlight_on, True)

            seq.run()

    #-----------------------------------------------------------------------
    def set_backlight_on(self, is_on, on_done=None):
        """Turn the backlight on or totally off.

        Args:
          is_on (bool): True to have the backlight on, False for off.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("KeypadLinc %s setting backlight to %s", self.label, is_on)
        cmd = 0x09 if is_on else 0x08
        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd, bytes([0x00] * 14))

        # This callback changes self._backlight if the command works.
        callback = functools.partial(self.handle_backlight_on, is_on=is_on)
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
        callback = functools.partial(self.handle_ack, task="Button on level")
        msg_handler = handler.StandardCmd(msg, callback, on_done)

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
        FLAG_BACKLIGHT = "backlight"
        FLAG_GROUP = "group"
        FLAG_ON_LEVEL = "on_level"
        FLAG_LOAD_ATTACH = "load_attached"
        FLAG_FOLLOW_MASK = "follow_mask"
        FLAG_OFF_MASK = "off_mask"
        FLAG_SIGNAL_BITS = "signal_bits"
        FLAG_NONTOGGLE_BITS = "nontoggle_bits"
        flags = set([FLAG_BACKLIGHT, FLAG_LOAD_ATTACH, FLAG_FOLLOW_MASK,
                     FLAG_SIGNAL_BITS, FLAG_NONTOGGLE_BITS, FLAG_OFF_MASK,
                     FLAG_GROUP, FLAG_ON_LEVEL])
        unknown = set(kwargs.keys()).difference(flags)
        if unknown:
            raise Exception("Unknown KeypadLinc flags input: %s.\n Valid "
                            "flags are: %s" % (unknown, flags))

        # Start a command sequence so we can call the flag methods in series.
        seq = CommandSeq(self.protocol, "KeypadLinc set_flags complete",
                         on_done)

        # Get the group if it was set.
        group = util.input_integer(kwargs, FLAG_GROUP)

        if FLAG_BACKLIGHT in kwargs:
            backlight = util.input_byte(kwargs, FLAG_BACKLIGHT)
            seq.add(self.set_backlight, backlight)

        if FLAG_LOAD_ATTACH in kwargs:
            load_attached = util.input_bool(kwargs, FLAG_LOAD_ATTACH)
            seq.add(self.set_load_attached, load_attached)

        if FLAG_ON_LEVEL in kwargs:
            on_level = util.input_byte(kwargs, FLAG_ON_LEVEL)
            seq.add(self.set_on_level, on_level)

        if FLAG_FOLLOW_MASK in kwargs:
            if group is None:
                raise Exception("follow_mask requires group=<NUM> to be input")

            mask = util.input_byte(kwargs, FLAG_FOLLOW_MASK)
            seq.add(self.set_led_follow_mask, group, mask)

        if FLAG_OFF_MASK in kwargs:
            if group is None:
                raise Exception("off_mask requires group=<NUM> to be input")

            mask = util.input_byte(kwargs, FLAG_OFF_MASK)
            seq.add(self.set_led_off_mask, group, mask)

        if FLAG_SIGNAL_BITS in kwargs:
            bits = util.input_byte(kwargs, FLAG_SIGNAL_BITS)
            seq.add(self.set_signal_bits, bits)

        if FLAG_NONTOGGLE_BITS in kwargs:
            bits = util.input_byte(kwargs, FLAG_NONTOGGLE_BITS)
            seq.add(self.set_nontoggle_bits, bits)

        seq.run()

    #-----------------------------------------------------------------------
    def set_led_follow_mask(self, group, mask, on_done=None):
        """Set the LED follow mask.

        The LED follow mask is a bitmask defined for each group (button),
        such that a value of 1 means that the associated button state will
        change it's state to match the state of the input group.

        So if button 1 is set to a follow mask of '0b00011100', then buttons
        3, 4, and 5 will change their state when button 1 changes it's state.

        This can be used to implement the 6 button keypadlinc by having
        button 1 control button 2 (and vice versa) and the same for buttons 7
        and 8.

        Args:
          group (int): The group (button) to set the follow fields for.
          mask (int): The bitmask value (8 bits) of the follow mask.  A bit
               value of 1 means that button will follow the state of the
               input group.
        """
        on_done = util.make_callback(on_done)

        task = "button {} follow mask: {:08b}".format(group, mask)
        LOG.info("KeypadLinc %s setting %s", self.addr, task)

        if group < 1 or group > 8:
            LOG.error("KeypadLinc group %s out of range [1,8]", group)
            on_done(False, "Invalid group", None)
            return

        # Copy out the correct set of bits.  A button can't follow itself so
        # skip that value.
        follow_mask = 0x00
        for i in range(1, 9):
            if i == group:
                continue

            is_set = util.bit_get(mask, i - 1)
            follow_mask = util.bit_set(follow_mask, i - 1, is_set)

        data = bytes([
            group,  # D1 must be group
            0x02,   # D2 set LED follow mask
            follow_mask,   # D3 bitmask value
            ] + [0x00] * 11)
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_ack, task=task)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

        # TODO: probably need to store this so button states can be set
        # correctly when the controlling button is pressed.
        # TODO: get button follow masks and save in db as part of refresh.

    #-----------------------------------------------------------------------
    def set_led_off_mask(self, group, mask, on_done=None):
        """Set the LED off mask.

        The LED off mask is a bitmask defined for each group (button).  The
        mask has 8 values (1 for each button).  If a bit in the mask has a
        value of 1, it means that the associated button will toggle to off
        when this button is pressed.

        So if button 1 is set to an off mask of '0b00011100', then buttons
        3, 4, and 5 will turn off when button 1 changes it's state.

        This is used to implement radio buttons by having all the other
        buttons in a group turn off when any other button in the group is
        pressed.

        Args:
          group (int): The group (button) to set the follow fields for.
          mask (int): The bitmask value (8 bits) of the follow mask.  A bit
               value of 1 means that button will turn off when the group
               button is pressed.
        """
        on_done = util.make_callback(on_done)

        task = "button {} off mask: {:08b}".format(group, mask)
        LOG.info("KeypadLinc %s setting %s", self.addr, task)

        if group < 1 or group > 8:
            LOG.error("KeypadLinc group %s out of range [1,8]", group)
            on_done(False, "Invalid group", None)
            return

        # Copy out the correct set of bits.  A button can't toggle itself off
        # so skip that value.
        off_mask = 0x00
        for i in range(1, 9):
            if i == group:
                continue

            is_set = util.bit_get(mask, i - 1)
            off_mask = util.bit_set(off_mask, i - 1, is_set)

        data = bytes([
            group,  # D1 must be group
            0x03,   # D2 set LED off mask
            off_mask,   # D3 bitmask value
            ] + [0x00] * 11)
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_ack, task=task)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

        # TODO: probably need to store this so button states can be set
        # correctly when the controlling button is pressed.
        # TODO: get button off masks and save in db as part of refresh.

    #-----------------------------------------------------------------------
    def set_signal_bits(self, signal_bits, on_done=None):
        """Set which signal is emitted for non-toggle buttons.

        This is a bit flag set (one bit per button) that is used when a
        button is set to be a non-toggle button (see set_nontoggle_bits).  If
        a button is set to non-toggle, then when it's pressed, it will emit
        either an ON signal if the signal bit for that button is 1) or an OFF
        signal if the signal bit for that button is 0.

        Args:
          signal_bits (int):  Signal bits for the 8 buttons.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        task = "signal bits: {:08b}".format(signal_bits)
        LOG.info("KeypadLinc %s setting %s", self.label, task)

        # Extended message data - see Insteon dev guide p156.
        data = bytes([
            0x01,   # D1 must be group 0x01
            0x0b,   # D2 set signal bits
            signal_bits,  # D3 signal bits
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_ack, task=task)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_nontoggle_bits(self, nontoggle_bits, on_done=None):
        """Set a button to be a toggle or non-toggle button.

        If a bit is zero, it's a toggle button which is the normal behavior.
        In that case, the button alternates between ON and OFF signals.

        If a bit is one, then the button is a non-toggle button.  The button
        will only emit one signal every time's pressed.  If the corresponding
        signal bit is 1, the signal will always be ON.  If it's 0, then it
        will always be off.  See set_signal_bits() for configuring those
        bits.

        Args:
          nontoggle_bits (int):  Non-toggle bits for the 8 buttons.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        task = "nontoggle bits: {:08b}".format(nontoggle_bits)
        LOG.info("KeypadLinc %s setting %s", self.label, task)

        # Extended message data - see Insteon dev guide p156.
        data = bytes([
            0x01,   # D1 must be group 0x01
            0x08,   # D2 set non-toggle bits
            nontoggle_bits,  # D3 signal bits
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_ack, task=task)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_ack(self, msg, on_done, task=""):
        """Callback for handling standard ack/nak.

        Other that reporting the result, no other action is taken.  It's used
        for commands that don't need any more processing.

        Args:
          msg (InpStandard):  The response message from the command.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
          task (str):  The message to report.
        """
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            on_done(True, "%s updated" % task, None)
        else:
            on_done(False, "%s failed" % task, None)

    #-----------------------------------------------------------------------
    def handle_backlight_on(self, msg, on_done, is_on):
        """Callback for handling turning the backlight on and off.

        Args:
          msg (InpStandard):  The response message from the command.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
          is_on (bool): True if the backlight is being turned on, False for
                off.
        """
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            on_done(True, "backlight set to %s" % is_on, None)
            self._backlight = is_on
        else:
            on_done(False, "backlight set failed", None)

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
        self._set_level(self._load_group, msg.cmd2,
                        reason=on_off.REASON_REFRESH)

    #-----------------------------------------------------------------------
    def handle_button_led(self, msg, on_done, group, is_on, led_bits,
                          reason=""):
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
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
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
            self._set_level(group, 0xff if is_on else 0x00, reason=reason)

            msg = "KeypadLinc %s LED group %s updated to %s" % \
                  (self.addr, group, is_on)
            on_done(True, msg, is_on)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc LED %s NAK error: %s, Message: %s",
                      self.addr, msg.nak_str(), msg)
            on_done(False, "KeypadLinc %s LED update failed. " + msg.nak_str(),
                    None)

    #-----------------------------------------------------------------------
    def handle_load_attach(self, msg, on_done, is_attached):
        """Callback for changing the load attached state.

        Args:
          msg (InpExtended): The reply message from the device.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
          is_attached (bool): True if the load is attached.
        """
        # If this it the ACK we're expecting, update the internal state and
        # emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)
            if is_attached:
                self._load_group = 1
            else:
                self._load_group = 9

            LOG.ui("Keypadlinc %s, setting load to group %s", self.addr,
                   self._load_group)
            on_done(True, "Load set to group: %s" % self._load_group, None)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc %s NAK error: %s", self.addr, msg)
            on_done(False, "Changing the load group failed", None)

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
        led_bits = msg.cmd2
        reason = on_off.REASON_REFRESH

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
                self._set_level(i + 1, 0xff if is_on else 0x00, reason=reason)

        self._led_bits = led_bits

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
        LOG.debug("KeypadLinc %s get button state: %s", self.addr, msg)

        # Extract the button actions.
        # non_toggle_mask = msg.data[9]
        # signal_mask = msg.data[12]
        # for i in range(0, 8):
        #     if util.bit_get(non_toggle_mask, i):
        #         if util.bit_get(signal_mask, i):
        #             self._actions[i] = Action.ON
        #         else:
        #             self._actions[i] = Action.OFF
        #     else:
        #         self._actions[i] = Action.TOGGLE

        #     LOG.ui("KeypadLinc %s group %d action = %s", self.addr,
        #            self._actions[i])

        #LED reason = on_off.REASON_REFRESH
        #LED led_bits = msg.data[10]

        #TODO: we can remove the 'handle_refresh_led' call and the command
        #      that caused it and replace it with the following commented out
        #      block of code:

        #LED LOG.ui("KeypadLinc %s setting LED bits %s", self.addr,
        #LED        "{:08b}".format(led_bits))

        #LED # Loop over the bits and emit a signal for any that have been
        #LED # changed.
        #LED for i in range(8):
        #LED     is_on = util.bit_get(led_bits, i)
        #LED     was_on = util.bit_get(self._led_bits, i)

        #LED     LOG.debug("Btn %d old: %d new %d", i + 1, is_on, was_on)
        #LED     if is_on != was_on:
        #LED         self._set_level(i + 1, 0xff if is_on else 0x00,
        #LED reason=reason)

        #LED self._led_bits = led_bits

        on_done(True, "Refresh complete", None)

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

        # If we have a saved reason from a simulated scene command, use that.
        # Otherwise the device button was pressed.  self.broadcast_done
        # already has the reason encoded in the callback so we don't have to
        # pass it in.
        reason = self.broadcast_reason if self.broadcast_reason else \
                 on_off.REASON_DEVICE
        self.broadcast_reason = ""

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
                self._set_level(msg.group, 0xff, mode, reason)

            # For an off command, we need to see if broadcast_done is active.
            # This is a generated broadcast and we need to manually turn the
            # device off so don't update it's state until that occurs.
            elif not self.broadcast_done:
                self._set_level(msg.group, 0x00, mode, reason)

        # Starting or stopping manual increment (cmd2 0x00=up, 0x01=down)
        elif on_off.Manual.is_valid(msg.cmd1):
            manual = on_off.Manual.decode(msg.cmd1, msg.cmd2)
            LOG.info("KeypadLinc %s manual change %s", self.addr, manual)

            self.signal_manual.emit(self, msg.group, manual, reason)

            # Non-load group buttons don't change state in manual mode. (found
            # through experiments)
            if msg.group == self._load_group:
                # Switches change state when the switch is held.
                if not self.is_dimmer:
                    if manual == on_off.Manual.UP:
                        self._set_level(0xff, on_off.Mode.MANUAL, reason)
                    elif manual == on_off.Manual.DOWN:
                        self._set_level(0x00, on_off.Mode.MANUAL, reason)

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
    def handle_set_load(self, msg, on_done, reason=""):
        """Callback for standard commanded messages to the load button.

        This callback is run when we get a reply back from one of our
        commands to the device for changing the load (usually group 1).  If
        the command was ACK'ed, we know it worked so we'll update the
        internal state of the device and emit the signals to notify others
        of the state change.

        Args:
          msg:  (message.InpStandard) The reply message from the device.
                The on/off level will be in the cmd2 field.
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
        """
        # If this is the ACK we're expecting, update the internal state and
        # emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)

            _is_on, mode = on_off.Mode.decode(msg.cmd1)
            self._set_level(self._load_group, msg.cmd2, mode, reason)
            on_done(True, "KeypadLinc state updated to %s" % self._level,
                    msg.cmd2)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc %s NAK error: %s", self.addr, msg)
            on_done(False, "KeypadLinc state update failed", None)

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
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)

            # Reason is device because we're simulating a button press.  We
            # can't really pass this around because we just get a broadcast
            # message later from the device.  So we set a temporary variable
            # here and use it in handle_broadcast() to output the reason.
            self.broadcast_reason = reason if reason else on_off.REASON_DEVICE
            on_done(True, "Scene triggered", None)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc %s NAK error: %s", self.addr, msg)
            on_done(False, "Scene trigger failed failed", None)

    #-----------------------------------------------------------------------
    def handle_increment(self, msg, on_done, delta, reason=""):
        """Callback for increment up/down commanded messages.

        This callback is run when we get a reply back from triggering an
        increment up or down on the device.  If the command was ACK'ed, we
        know it worked.

        Args:
          msg (message.InpStandard): The reply message from the device.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
          delta (int):  The amount +/- of level to change by.
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
        """
        # If this it the ACK we're expecting, update the internal state and
        # emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)

            # Add the delta and bound at [0, 255]
            level = min(self._level + delta, 255)
            level = max(level, 0)
            self._set_level(self._load_group, level, reason=reason)

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

        reason = on_off.REASON_SCENE

        # The local button being modified is stored in the db entry.
        localGroup = entry.data[2]

        # Handle on/off codes
        if on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)

            # For switches, on/off determines the level.  For dimmers, it's
            # set by the responder entry in the database.
            level = 0xff if is_on else 0x00
            if self.is_dimmer and is_on and localGroup == self._load_group:
                level = entry.data[0]

            self._set_level(localGroup, level, mode, reason)

        # Increment up 1 unit which is 8 levels.
        elif msg.cmd1 == 0x15:
            assert localGroup == self._load_group
            self._set_level(localGroup, min(0xff, self._level + 8),
                            reason=reason)

        # Increment down 1 unit which is 8 levels.
        elif msg.cmd1 == 0x16:
            assert msg.group == self._load_group
            self._set_level(localGroup, max(0x00, self._level - 8),
                            reason=reason)

        # Starting/stopping manual increment (cmd2 0x00=up, 0x01=down)
        elif on_off.Manual.is_valid(msg.cmd1):
            manual = on_off.Manual.decode(msg.cmd1, msg.cmd2)
            self.signal_manual.emit(self, localGroup, manual, reason)

            # If the button is released, refresh to get the final level in
            # dimming mode since we don't know where the level stopped.
            if manual == on_off.Manual.STOP:
                self.refresh()

        else:
            LOG.warning("KeypadLinc %s unknown cmd %#04x", self.addr,
                        msg.cmd1)

    #-----------------------------------------------------------------------
    def _set_level(self, group, level, mode=on_off.Mode.NORMAL, reason=""):
        """Update the device level state for a group.

        This will change the internal state and emit the state changed
        signals.  It is called by whenever we're informed that the device has
        changed state.

        Args:
          group (int):  The group number to update [1,8].
          level (int):  The new device level in the range [0,255].  0 is off.
          mode (on_off.Mode): The type of on/off that was triggered (normal,
               fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
        """
        LOG.info("Setting device %s grp=%s on=%s %s%s", self.label, group,
                 level, mode, reason)

        if group == self._load_group:
            self._level = level

        # Update the LED bits in the correct slot.
        if group < 9:
            self._led_bits = util.bit_set(self._led_bits, group - 1,
                                          1 if level else 0)

        self.signal_level_changed.emit(self, group, level, mode, reason)

    #-----------------------------------------------------------------------
