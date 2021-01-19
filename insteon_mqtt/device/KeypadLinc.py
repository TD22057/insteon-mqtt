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
from . import functions
from . import Dimmer

LOG = log.get_logger()


#===========================================================================
class KeypadLinc(functions.SetAndState, functions.Scene, functions.Backlight,
                 Base):
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

    - signal_state( Device, int level, on_off.Mode mode, str reason):
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
        self.signal_state = Signal()

        # Manual mode start up, down, off
        # API: func(Device, int group, on_off.Manual mode, str reason)
        self.signal_manual = Signal()

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

        if self.is_dimmer:
            self.cmd_map.update({
                'increment_up' : self.increment_up,
                'increment_down' : self.increment_down,
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
        self.set_flags_map.update({'on_level': self.set_on_level,
                                   'ramp_rate': self.set_ramp_rate,
                                   'group': None,
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

        seq = CommandSeq(self, "Refresh complete", on_done, name="DevRefresh")

        # TODO: change this to 0x2e get extended which reads on mask, off
        # mask, on level, led brightness, non-toggle mask, led bit mask (led
        # on/off), on/off bit mask, etc (see keypadlinc manual)

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
        #self._load_group
        callback = functools.partial(self.handle_refresh,
                                     group=self._load_group)
        msg_handler = handler.DeviceRefresh(self, callback, force,
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
    def cmd_on_values(self, mode, level, transition, group):
        """Calculate Cmd Values for On

        Args:
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          level (int): On level between 0-255.
          transition (int): Ramp rate for the transition in seconds.
          group (int): The group number that this state applies to. Defaults
                       to None.
        Returns
          cmd1, cmd2 (int): Value of cmds for this device.
        """
        if not self.is_dimmer:
            level = 0xff
        # TODO this is directly copied from Dimmer, would be better to have
        # this as shared code.
        elif level is None:
            # Not specified - choose brightness as pressing the button would do
            if mode == on_off.Mode.FAST:
                # Fast-ON command.  Use full-brightness.
                level = 0xff
            else:
                # Normal/instant ON command.  Use default on-level.
                # Check if we saved the default on-level in the device
                # database when setting it.
                level = self.get_on_level()
                if self._level == level:
                    # Just like with button presses, if already at default on
                    # level, go to full brightness.
                    level = 0xff

        mode, transition = self.mode_transition_supported(mode, transition)

        cmd1 = on_off.Mode.encode(True, mode)
        cmd2 = on_off.Mode.encode_cmd2(True, mode, level, transition)
        return (cmd1, cmd2)

    #-----------------------------------------------------------------------
    def cmd_off_values(self, mode, transition, group):
        """Calculate Cmd Values for Off

        Args:
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          transition (int): Ramp rate for the transition in seconds.
          group (int): The group number that this state applies to. Defaults
                       to None.
        Returns
          cmd1, cmd2 (int): Value of cmds for this device.
        """
        # Ignore RAMP mode / transition if command not supported
        mode, transition = self.mode_transition_supported(mode, transition)
        cmd1 = on_off.Mode.encode(False, mode)
        cmd2 = on_off.Mode.encode_cmd2(True, mode, 0, transition)
        return (cmd1, cmd2)

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
            if not self.is_dimmer or not self.on_off_ramp_supported:
                if self.db.desc is None:
                    LOG.error("Model info not in DB - ignoring ramp "
                              "rate.  Use 'get_model %s' to retrieve.",
                              self.addr)
                else:
                    LOG.error("Light ON at Ramp Rate not supported with "
                              "%s devices - ignoring specified ramp rate.",
                              self.db.desc.model)
                transition = None
                if mode == on_off.Mode.RAMP:
                    mode = on_off.Mode.NORMAL
        return (mode, transition)

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
            if 'ramp_rate' in data:
                data_2 = 0x1f
                for ramp_key, ramp_value in Dimmer.ramp_pretty.items():
                    if data['ramp_rate'] >= ramp_value:
                        data_2 = ramp_key
                        break
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
        for ramp_key, ramp_value in Dimmer.ramp_pretty.items():
            if ramp_rate <= ramp_key:
                ramp_rate = ramp_value
                break
        LOG.ui("Dimmer %s on_level: %s (%.2f%%) ramp rate: %ss", self.label,
               on_level, on_level / 2.55, ramp_rate)
        on_done(True, "Operation complete", msg.data[5])

    #-----------------------------------------------------------------------
    def set_on_level(self, on_done=None, **kwargs):
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

        # Check for valid input
        level = util.input_byte(kwargs, 'on_level')
        if level is None:
            LOG.error("Invalid on level.")
            on_done(False, 'Invalid on level.', None)
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
        callback = functools.partial(self.handle_on_level, level=level)
        msg_handler = handler.StandardCmd(msg, callback, on_done)

        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_ramp_rate(self, on_done=None, **kwargs):
        """Set the device default ramp rate.

        This changes the dimmer default ramp rate of how quickly the it
        will turn on or off. This rate can be between 0.1 seconds and up
        to 9 minutes.

        Args:
          rate (float): Ramp rate in in the range [0.1, 540] seconds
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        if not self.is_dimmer:
            LOG.error("KeypadLinc %s switch doesn't support setting ramp_rate",
                      self.addr)
            return

        # Check for valid input
        rate = util.input_float(kwargs, 'ramp_rate')
        if rate is None:
            LOG.error("Invalid ramp rate.")
            on_done(False, 'Invalid ramp rate.', None)
            return

        LOG.info("Dimmer %s setting ramp rate to %s", self.label, rate)

        data_3 = 0x1c  # the default ramp rate is .5
        for ramp_key, ramp_value in Dimmer.ramp_pretty.items():
            if rate >= ramp_value:
                data_3 = ramp_key
                break

        # Extended message data - see Insteon dev guide p156.
        data = bytes([
            0x01,   # D1 must be group 0x01
            0x05,   # D2 set ramp rate when button is pressed
            data_3,  # D3 rate
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = self.generic_ack_callback("Button ramp rate updated.")
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
    def handle_on_level(self, msg, on_done, level):
        """Callback for handling set_on_level() responses.

        This is called when we get a response to the set_on_level() command.
        Update stored on-level in device DB and call the on_done callback with
        the status.

        Args:
          msg (InpStandard): The response message from the command.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        self.db.set_meta('on_level', level)
        on_done(True, "Button on level updated", None)

    #-----------------------------------------------------------------------
    def get_on_level(self):
        """Look up previously-set on-level in device database, if present

        This is called when we need to look up what is the default on-level
        (such as when getting an ON broadcast message from the device).

        If on_level is not found in the DB, assumes on-level is full-on.
        """
        on_level = self.db.get_meta('on_level')
        if on_level is None:
            on_level = 0xff
        return on_level

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
    def handle_on_off(self, msg):
        """Handle on_off broadcast messages from this device.

        This is called from base.handle_broadcast using the group_map map.

        Args:
          msg (InpStandard):  Broadcast message from the device.
        """
        # Non-group 1 messages are for the scene buttons on keypadlinc.
        # Treat those the same as the remote control does.  They don't have
        # levels to find/set but have similar messages to the dimmer load.

        # If we have a saved reason from a simulated scene command, use that.
        # Otherwise the device button was pressed.
        reason = self.broadcast_reason if self.broadcast_reason else \
                 on_off.REASON_DEVICE
        self.broadcast_reason = ""

        # On/off commands.
        if on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)
            LOG.info("KeypadLinc %s broadcast grp: %s on: %s mode: %s",
                     self.addr, msg.group, is_on, mode)

            # For an on command, we can update directly.
            if is_on:
                # Level isn't provided in the broadcast msg.
                # What to use depends on which command was received.
                if msg.group != self._load_group:
                    # Only load group can be a dimmer, use full-on for others
                    level = 0xff
                elif mode == on_off.Mode.FAST:
                    # Fast-ON command.  Use full-brightness.
                    level = 0xff
                else:
                    # Normal/instant ON command.  Use default on-level.
                    # Check if we saved the default on-level in the device
                    # database when setting it.
                    level = self.get_on_level()
                    if self._level == level:
                        # Pressing on again when already at the default on
                        # level causes the device to go to full-brightness.
                        level = 0xff
                self._set_state(group=msg.group, level=level, mode=mode,
                                reason=reason)

            else:
                self._set_state(group=msg.group, level=0x00, mode=mode,
                                reason=reason)

        # Starting or stopping manual increment (cmd2 0x00=up, 0x01=down)
        elif on_off.Manual.is_valid(msg.cmd1):
            manual = on_off.Manual.decode(msg.cmd1, msg.cmd2)
            LOG.info("KeypadLinc %s manual change %s", self.addr, manual)

            self.signal_manual.emit(self, button=msg.group, manual=manual,
                                    reason=reason)

            # Non-load group buttons don't change state in manual mode. (found
            # through experiments)
            if msg.group == self._load_group:
                # Switches change state when the switch is held.
                if not self.is_dimmer:
                    if manual == on_off.Manual.UP:
                        self._set_state(group=self._load_group, level=0xff,
                                        mode=on_off.Mode.MANUAL,
                                        reason=reason)
                    elif manual == on_off.Manual.DOWN:
                        self._set_state(group=self._load_group, level=0x00,
                                        mode=on_off.Mode.MANUAL,
                                        reason=reason)

                # Ping the device to get the dimmer states - we don't know
                # what the keypadlinc things the state is - could be on or
                # off.  Doing a dim down for a long time puts all the other
                # devices "off" but the keypadlinc can still think that it's
                # on.  So we have to do a refresh to find out.
                elif manual == on_off.Manual.STOP:
                    self.refresh()

        self.update_linked_devices(msg)

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
        LOG.debug("KeypadLinc %s ACK: %s", self.addr, msg)

        # Add the delta and bound at [0, 255]
        level = min(self._level + delta, 255)
        level = max(level, 0)
        self._set_state(group=self._load_group, level=level, reason=reason)

        s = "KeypadLinc %s state updated to %s" % (self.addr, self._level)
        on_done(True, s, msg.cmd2)

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

            self._set_state(group=localGroup, level=level, mode=mode,
                            reason=reason)

        # Increment up 1 unit which is 8 levels.
        elif msg.cmd1 == 0x15:
            assert localGroup == self._load_group
            self._set_state(group=localGroup, level=min(0xff,
                                                        self._level + 8),
                            reason=reason)

        # Increment down 1 unit which is 8 levels.
        elif msg.cmd1 == 0x16:
            assert msg.group == self._load_group
            self._set_state(group=localGroup, level=max(0x00,
                                                        self._level - 8),
                            reason=reason)

        # Starting/stopping manual increment (cmd2 0x00=up, 0x01=down)
        elif on_off.Manual.is_valid(msg.cmd1):
            manual = on_off.Manual.decode(msg.cmd1, msg.cmd2)
            self.signal_manual.emit(self, button=localGroup, manual=manual,
                                    reason=reason)

            # If the button is released, refresh to get the final level in
            # dimming mode since we don't know where the level stopped.
            if manual == on_off.Manual.STOP:
                self.refresh()

        else:
            LOG.warning("KeypadLinc %s unknown cmd %#04x", self.addr,
                        msg.cmd1)

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
