#===========================================================================
#
# KeypadLinc module
#
#===========================================================================
import functools
from .. import handler
from .. import log
from .. import message as Msg
from .. import on_off
from .. import util
from .base import ResponderBase
from .functions import Scene, Backlight, ManualCtrl

LOG = log.get_logger()


#===========================================================================
class KeypadLinc(Scene, Backlight, ManualCtrl, ResponderBase):
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
    the device (like sending MQTT messages).
    """

    #-----------------------------------------------------------------------
    def __init__(self, protocol, modem, address, name):
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
        self.type_name = "keypad_linc_sw"

        # Remote (mqtt) commands mapped to methods calls.  Add to the base
        # class defined commands.
        self.cmd_map.update({
            'set_button_led' : self.set_button_led,
            'set_load_attached' : self.set_load_attached,
            'set_led_follow_mask' : self.set_led_follow_mask,
            'set_led_off_mask' : self.set_led_off_mask,
            'set_signal_bits' : self.set_signal_bits,
            'set_nontoggle_bits' : self.set_nontoggle_bits,
            })

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

        # Update the group map with the groups to be paired and the handler
        # for broadcast messages from this group
        # We don't configure for the distinction between 6 and 8 keypads
        # pairing extra groups doesn't do any harm.
        self.group_map.update({0x01: self.handle_on_off,
                               0x02: self.handle_on_off,
                               0x03: self.handle_on_off,
                               0x04: self.handle_on_off,
                               0x05: self.handle_on_off,
                               0x06: self.handle_on_off,
                               0x07: self.handle_on_off,
                               0x08: self.handle_on_off})

        # List of responder group numbers
        self.responder_groups = [1, 2, 3, 4, 5, 6, 7, 8, 9]

        # Define the flags handled by set_flags()
        self.set_flags_map.update({'group': None,
                                   'load_attached': self.set_load_attached,
                                   'follow_mask': self.set_led_follow_mask,
                                   'off_mask': self.set_led_off_mask,
                                   'signal_bits': self.set_signal_bits,
                                   'nontoggle_bits': self.set_nontoggle_bits})

    #-----------------------------------------------------------------------
    @property
    def on_off_ramp_supported(self):
        """Returns True if the "Light ON at Ramp Rate" and "Light OFF at Ramp
        Rate" commands are supported by this device and False if not (or if
        not known).
        """
        if self.db.desc is None:
            # Don't know device model yet.  Use "get_model" command to get it.
            return False
        else:
            return (self.db.desc.model == "2334-222" or
                    self.db.desc.model == "2334-232")

    #-----------------------------------------------------------------------
    def refresh(self, force=False, group=None, on_done=None):
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
        # Needed to pass the _load_group data to base refresh()
        group = group if group is not None else self._load_group
        super().refresh(force=force, group=group, on_done=on_done)

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
        super().addRefreshData(seq, force)

        # TODO: change this to 0x2e get extended which reads on mask, off
        # mask, on level, led brightness, non-toggle mask, led bit mask (led
        # on/off), on/off bit mask, etc (see keypadlinc manual)

        # First send a refresh command which gets the state of the LED's by
        # returning a bit flag.  Pass skip_db here - we'll let the second
        # refresh handler below take care of getting the database updated.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x01)
        msg_handler = handler.DeviceRefresh(self, self.handle_refresh_led,
                                            force=False, num_retry=3,
                                            skip_db=True)
        seq.add_msg(msg, msg_handler)

        # Get the state of which buttons toggle and the signal they emit.
        # Since the values we are interested in will be returned regardless
        # of the group number we use, we just use group 1.
        data = bytes([0x01] + [0x00] * 13)
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)
        msg_handler = handler.ExtendedCmdResponse(msg,
                                                  self.handle_refresh_state)
        seq.add_msg(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set(self, is_on=None, level=None, group=0x00, mode=on_off.Mode.NORMAL,
            reason="", transition=None, on_done=None):
        """Turn the device on or off.  Level zero will be off.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          is_on (bool): True to turn on, False for off
          level (int): If non zero, turn the device on.  Should be in the
                range 0 to 255.  If None, use default on-level.
          group (int): The group to send the command to. If the group is 0,
                it will always be the load (whether it's attached or not).
                Otherwise it must be in the range [1,8] and controls the
                specific button.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          transition (int): The transition ramp_rate if supported.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        super().set(is_on=is_on, level=level, group=group, mode=mode,
                    reason=reason, transition=transition, on_done=on_done)

    #-----------------------------------------------------------------------
    def on(self, group=0x00, level=None, mode=on_off.Mode.NORMAL, reason="",
           transition=None, on_done=None):
        """Turn the device on.

        This is a wrapper around the SetAndState functions class, that adds
        a few unique KPL functions.

        Args:
          group (int):  The group to send the command to.  If the group is 0,
                it will always be the load (whether it's attached or not).
                Otherwise it must be in the range [1,8] and controls the
                specific button.
          level (int):  If non-zero, turn the device on.  The API is an int
                to keep a consistent API with other devices.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          transition (int): Transition time in seconds if supported.
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # If the group is 0, use the load group.
        group = self._load_group if group == 0 else group

        # Non-load buttons are turned on/off via the LED command.
        if group != self._load_group:
            self.set_button_led(group, True, reason, on_done)
        else:
            # This is a regular on command pass to SetAndState class
            super().on(group=group, level=level, mode=mode, reason=reason,
                       transition=transition, on_done=on_done)

    #-----------------------------------------------------------------------
    def off(self, group=0x00, mode=on_off.Mode.NORMAL, reason="",
            transition=None, on_done=None):
        """Turn the device off.

        This is a wrapper around the SetAndState functions class, that adds
        a few unique KPL functions.

        Args:
          group (int):  The group to send the command to.  If the group is 0,
                it will always be the load (whether it's attached or not).
                Otherwise it must be in the range [1,8] and controls the
                specific button.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          transition (int): Transition time in seconds if supported.
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # If the group is 0, use the load group.
        group = self._load_group if group == 0 else group

        # Non-load buttons are turned on/off via the LED command.
        if group != self._load_group:
            self.set_button_led(group, False, reason, on_done)
        else:
            # This is a regular on command pass to SetAndState class
            super().off(group=group, mode=mode, reason=reason,
                        transition=transition, on_done=on_done)

    #-----------------------------------------------------------------------
    def mode_transition_supported(self, mode, transition):
        """Adjust Mode and Transition based on Device Support

        Args:
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          transition (int): Ramp rate for the transition in seconds.
        Returns
          mode, transition: The adjusted values.
        """
        # Ignore RAMP mode / transition if command not supported
        if mode == on_off.Mode.RAMP or transition is not None:
            LOG.error("Light ON at Ramp Rate not supported with "
                      "non-dimming devices - ignoring specified ramp rate.")
            transition = None
            if mode == on_off.Mode.RAMP:
                mode = on_off.Mode.NORMAL
        return (mode, transition)

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
           D1: on level for switches (0xff)
           D2: 0x00
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
            defaults = [0xff, 0x00, group]

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
        data_3 = data.get('group', data_3)
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
    def set_led_follow_mask(self, on_done=None, **kwargs):
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

        # Check for valid input
        group = util.input_byte(kwargs, 'group')
        if group is None:
            LOG.error("follow_mask requires group=<NUM> to be input")
            on_done(False, 'Invalid group specified.', None)
            return
        mask = util.input_byte(kwargs, 'follow_mask')
        if mask is None:
            LOG.error("Invalid follow mask.")
            on_done(False, 'Invalid follow mask.', None)
            return

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
        callback = self.generic_ack_callback(task)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

        # TODO: probably need to store this so button states can be set
        # correctly when the controlling button is pressed.
        # TODO: get button follow masks and save in db as part of refresh.

    #-----------------------------------------------------------------------
    def set_led_off_mask(self, on_done=None, **kwargs):
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

        # Check for valid input
        group = util.input_byte(kwargs, 'group')
        if group is None:
            LOG.error("off_mask requires group=<NUM> to be input")
            on_done(False, 'Invalid group specified.', None)
            return
        mask = util.input_byte(kwargs, 'off_mask')
        if mask is None:
            LOG.error("Invalid off mask.")
            on_done(False, 'Invalid off mask.', None)
            return

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
        callback = self.generic_ack_callback(task)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

        # TODO: probably need to store this so button states can be set
        # correctly when the controlling button is pressed.
        # TODO: get button off masks and save in db as part of refresh.

    #-----------------------------------------------------------------------
    def set_signal_bits(self, on_done=None, **kwargs):
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
        # Check for valid input
        signal_bits = util.input_byte(kwargs, 'signal_bits')
        if signal_bits is None:
            LOG.error("Invalid signal bits.")
            on_done(False, 'Invalid signal bits.', None)
            return

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
        callback = self.generic_ack_callback(task)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_nontoggle_bits(self, on_done=None, **kwargs):
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
        # Check for valid input
        nontoggle_bits = util.input_byte(kwargs, 'nontoggle_bits')
        if nontoggle_bits is None:
            LOG.error("Invalid nontoggle bits.")
            on_done(False, 'Invalid nontoggle bits.', None)
            return

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
        callback = self.generic_ack_callback(task)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

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
        LOG.debug("KeypadLinc LED %s group %s ACK: %s", self.addr, group,
                  msg)

        # Update the LED bit for the updated group.
        self._led_bits = led_bits
        LOG.ui("KeypadLinc %s LED's changed to %s", self.addr,
               "{:08b}".format(self._led_bits))

        # Change the level and emit the active signal.
        self._set_state(group=group, level=0xff if is_on else 0x00,
                        reason=reason)

        msg = "KeypadLinc %s LED group %s updated to %s" % \
              (self.addr, group, is_on)
        on_done(True, msg, is_on)

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
        LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)
        if is_attached:
            self._load_group = 1
        else:
            self._load_group = 9

        LOG.ui("Keypadlinc %s, setting load to group %s", self.addr,
               self._load_group)
        on_done(True, "Load set to group: %s" % self._load_group, None)

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
                self._set_state(group=i + 1, level=0xff if is_on else 0x00,
                                reason=reason)

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
        #LED         self._set_state(i + 1, 0xff if is_on else 0x00,
        #LED reason=reason)

        #LED self._led_bits = led_bits

        on_done(True, "Refresh complete", None)

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
        if group == self._load_group:
            # Switches change state when the switch is held.
            if manual == on_off.Manual.UP:
                self._set_state(group=self._load_group, level=0xff,
                                mode=on_off.Mode.MANUAL,
                                reason=reason)
            elif manual == on_off.Manual.DOWN:
                self._set_state(group=self._load_group, level=0x00,
                                mode=on_off.Mode.MANUAL,
                                reason=reason)
        else:
            # Non-load group buttons don't change state in manual mode. (found
            # through experiments).  It looks like they turn on from off but
            # not off from on?? Use refresh to be sure.
            if manual == on_off.Manual.STOP:
                self.refresh()

    #-----------------------------------------------------------------------
    def group_cmd_local_group(self, entry):
        """Get the Local Group Affected by this Group Command

        For most devices this is group 1, but for multigroup devices such
        as the KPL, they may need to decode the local group from the
        entry data.

        Args:
          entry (DeviceEntry):  The local db entry for this group command.
        Returns:
          group (int):  The local group affected
        """
        return entry.data[2]

    #-----------------------------------------------------------------------
    def _cache_state(self, group, is_on, level, reason):
        """Cache the State of the Device

        Used to help with the KPL unique functions.

        Args:
          group (int): The group which this applies
          is_on (bool): Whether the device is on.
          level (int): The new device level in the range [0,255].  0 is off.
          reason (str): Reason string to pass around.
        """
        if is_on is not None:
            self._is_on = is_on
        group = 0x01 if group is None else group
        if group == self._load_group:
            self._level = level

        # Update the LED bits in the correct slot.
        if group < 9:
            self._led_bits = util.bit_set(self._led_bits, group - 1,
                                          1 if level else 0)

    #-----------------------------------------------------------------------
