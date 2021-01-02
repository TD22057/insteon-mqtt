#===========================================================================
#
# Dimmer device module.  Used for anything that acts like a dimmer
# including wall switches, lamp modules, and some remotes.
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


class Dimmer(Base):
    """Insteon dimmer device.

    This class can be used to model any device that acts like a dimmer
    including wall switches, lamp modules, and some remotes.

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).  Supported signals are:

    - signal_level_changed( Device, int level, on_off.Mode mode, str reason ):
      Sent whenever the dimmer is turned on or off or changes level.  The
      level field will be in the range 0-255.

    - signal_manual( Device, on_off.Manual mode, str reason ): Sent when the
      device starts or stops manual mode (when a button is held down or
      released).
    """

    # Mapping of ramp rates to human readable values
    ramp_pretty = {0x00: 540, 0x01: 480, 0x02: 420, 0x03: 360, 0x04: 300,
                   0x05: 270, 0x06: 240, 0x07: 210, 0x08: 180, 0x09: 150,
                   0x0a: 120, 0x0b: 90, 0x0c: 60, 0x0d: 47, 0x0e: 43, 0x0f: 39,
                   0x10: 34, 0x11: 32, 0x12: 30, 0x13: 28, 0x14: 26,
                   0x15: 23.5, 0x16: 21.5, 0x17: 19, 0x18: 8.5, 0x19: 6.5,
                   0x1a: 4.5, 0x1b: 2, 0x1c: .5, 0x1d: .3, 0x1e: .2, 0x1f: .1}

    def __init__(self, protocol, modem, address, name=None):
        """Constructor

        Args:
          protocol (Protocol): The Protocol object used to communicate
                   with the Insteon network.  This is needed to allow the
                   device to send messages to the PLM modem.
          modem (Modem): The Insteon modem used to find other devices.
          address (Address): The address of the device.
          name (str): Nice alias name to use for the device.
        """
        super().__init__(protocol, modem, address, name)

        # Current dimming level. 0x00 -> 0xff
        self._level = 0x00

        # Support dimmer style signals and motion on/off style signals.
        # API:  func(Device, int level, on_off.Mode mode, str reason)
        self.signal_level_changed = Signal()

        # Manual mode start up, down, off
        # API: func(Device, on_off.Manual mode, str reason)
        self.signal_manual = Signal()

        # Remote (mqtt) commands mapped to methods calls.  Add to the base
        # class defined commands.
        self.cmd_map.update({
            'on' : self.on,
            'off' : self.off,
            'set' : self.set,
            'increment_up' : self.increment_up,
            'increment_down' : self.increment_down,
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
          group (int): The group to send the command to.  For this device,
                this must be 1.  Allowing a group here gives us a consistent
                API to the on command across devices.
          level (int): If non zero, turn the device on.  Should be in the
                range 0 to 255.  If None, use default on-level.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Dimmer %s cmd: on %s", self.addr, level)
        if level is None:
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
        assert level >= 0 and level <= 0xff
        assert group == 0x01
        assert isinstance(mode, on_off.Mode)

        # Send the requested on code value.
        cmd1 = on_off.Mode.encode(True, mode)
        msg = Msg.OutStandard.direct(self.addr, cmd1, level)

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
          group (int): The group to send the command to.  For this device,
                this must be 1.  Allowing a group here gives us a consistent
                API to the on command across devices.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Dimmer %s cmd: off", self.addr)
        assert group == 0x01
        assert isinstance(mode, on_off.Mode)

        # Send an off or instant off command.
        cmd1 = on_off.Mode.encode(False, mode)
        msg = Msg.OutStandard.direct(self.addr, cmd1, 0x00)

        # Use the standard command handler which will notify us when
        # the command is ACK'ed.
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
          level (int): If non zero, turn the device on.  Should be in the
                range 0 to 255.  If None, use default on-level.
          group (int): The group to send the command to.  For this device,
                this must be 1.  Allowing a group here gives us a consistent
                API to the on command across devices.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        if (level is None) or level:
            # None/True == use default on-level.  Since true is integer 1,
            # do an explicit check here to catch that input.
            if level is True:
                level = None

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
          is_on (bool): True for an on command, False for an off command.
          group (int): The group on the device to simulate.  For this device,
                this must be 1.
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Dimmer %s scene %s", self.addr, "on" if is_on else "off")
        assert group == 0x01

        # Send an 0x30 all link command to simulate the button being pressed
        # on the switch.  See page 163 of insteon dev guide
        cmd1 = 0x11 if is_on else 0x13
        data = bytes([
            group,  # D1 = group (button)
            0x00,   # D2 = use level in scene db
            0x00,   # D3 = on level if D2=0x01
            cmd1,   # D4 = cmd1 to send
            0x01,   # D5 = cmd2 to send
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
        LOG.info("Dimmer %s cmd: increment up", self.addr)

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
        LOG.info("Dimmer %s cmd: increment down", self.addr)

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
            defaults = [0x03, 0x00, 0x01]

        # Responder data is always link dependent.  Since nothing was given,
        # assume the user wants to turn the device on (0xff).
        else:
            defaults = [0xff, 0x1f, 0x01]

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
        ret = [{'data_1': data[0]}, {'data_2': data[1]}, {'data_3': data[2]}]
        if not is_controller:
            ramp = 0x1f  # default
            if data[1] in self.ramp_pretty:
                ramp = self.ramp_pretty[data[1]]
            on_level = int((data[0] / .255) + .5) / 10
            ret = [{'on_level': on_level},
                   {'ramp_rate': ramp},
                   {'data_3': data[2]}]
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
        if not is_controller:
            if 'ramp_rate' in data:
                data_2 = 0x1f
                for ramp_key, ramp_value in self.ramp_pretty.items():
                    if data['ramp_rate'] >= ramp_value:
                        data_2 = ramp_key
                        break
            if 'on_level' in data:
                data_1 = int(data['on_level'] * 2.55 + .5)
        return [data_1, data_2, data_3]

    #-----------------------------------------------------------------------
    def set_backlight(self, level, on_done=None):
        """Set the device backlight level.

        This changes the level of the LED back light that is used by the
        device status LED's (dimmer levels, KeypadLinc buttons, etc).

        The default factory level is 0x1f.

        Args:
          level (int): The backlight level in the range [0,255]
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Dimmer %s setting backlight to %s", self.label, level)

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
        for ramp_key, ramp_value in self.ramp_pretty.items():
            if ramp_rate <= ramp_key:
                ramp_rate = ramp_value
                break
        LOG.ui("Dimmer %s on_level: %s (%.2f%%) ramp rate: %ss", self.label,
               on_level, on_level / 2.55, ramp_rate)
        on_done(True, "Operation complete", msg.data[5])

    #-----------------------------------------------------------------------
    def set_on_level(self, level, on_done=None):
        """Set the device default on level.

        This changes the dimmer level the device will go to when the on
        button is pressed.  This can be very useful because a double-tap
        (fast-on) will the turn the device to full brightness if needed.

        Args:
          level (int): The default on level in the range [0,255]
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Dimmer %s setting on level to %s", self.label, level)

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
    def set_ramp_rate(self, rate, on_done=None):
        """Set the device default ramp rate.

        This changes the dimmer default ramp rate of how quickly it will
        turn on or off. This rate can be between 0.1 seconds and up to 9
        minutes.

        Args:
          rate (float): Ramp rate in in the range [0.1, 540] seconds
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Dimmer %s setting ramp rate to %s", self.label, rate)

        data_3 = 0x1c  # the default ramp rate is .5
        for ramp_key, ramp_value in self.ramp_pretty.items():
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
        msg_handler = handler.StandardCmd(msg, self.handle_ramp_rate, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_flags(self, on_done, **kwargs):
        """Set internal device flags.

        This command is used to change internal device flags and states.
        Valid inputs are:

        - backlight=level: Change the backlight LED level (0-255).  See
          set_backlight() for details.

        - on_level=level: Change the default device on level (0-255) See
          set_on_level for details.

        Args:
          kwargs: Key=value pairs of the flags to change.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Dimmer %s cmd: set flags", self.label)

        # Check the input flags to make sure only ones we can understand were
        # passed in.
        FLAG_BACKLIGHT = "backlight"
        FLAG_ON_LEVEL = "on_level"
        FLAG_RAMP_RATE = "ramp_rate"
        flags = set([FLAG_BACKLIGHT, FLAG_ON_LEVEL, FLAG_RAMP_RATE])
        unknown = set(kwargs.keys()).difference(flags)
        if unknown:
            raise Exception("Unknown Dimmer flags input: %s.\n Valid flags "
                            "are: %s" % unknown, flags)

        # Start a command sequence so we can call the flag methods in series.
        seq = CommandSeq(self, "Dimmer set_flags complete", on_done,
                         name="SetFlags")

        if FLAG_BACKLIGHT in kwargs:
            backlight = util.input_byte(kwargs, FLAG_BACKLIGHT)
            seq.add(self.set_backlight, backlight)

        if FLAG_ON_LEVEL in kwargs:
            on_level = util.input_byte(kwargs, FLAG_ON_LEVEL)
            seq.add(self.set_on_level, on_level)

        if FLAG_RAMP_RATE in kwargs:
            rate = util.input_float(kwargs, FLAG_RAMP_RATE)
            seq.add(self.set_ramp_rate, rate)

        seq.run()

    #-----------------------------------------------------------------------
    def handle_backlight(self, msg, on_done):
        """Callback for handling set_backlight() responses.

        This is called when we get a response to the set_backlight() command.
        We don't need to do anything - just call the on_done callback with
        the status.

        Args:
          msg (InpStandard): The response message from the command.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        on_done(True, "Backlight level updated", None)

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
    def handle_ramp_rate(self, msg, on_done):
        """Callback for handling set_ramp_rate() responses.

        This is called when we get a response to the set_ramp_rate() command.
        We don't need to do anything - just call the on_done callback with
        the status.

        Args:
          msg (InpStandard): The response message from the command.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            on_done(True, "Button ramp rate updated", None)
        else:
            on_done(False, "Button ramp rate failed", None)

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
    def handle_on_off(self, msg):
        """Handle broadcast messages from this device.

        This is called from base.handle_broadcast using the group_map map.

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
            LOG.info("Dimmer %s broadcast ACK grp: %s", self.addr, msg.group)
            if self.broadcast_done:
                self.broadcast_done()
            self.broadcast_done = None
            return

        # On/off commands.
        elif on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)
            LOG.info("Dimmer %s broadcast grp: %s on: %s mode: %s", self.addr,
                     msg.group, is_on, mode)

            # For an on command, we can update directly.
            if is_on:
                # Level isn't provided in the broadcast msg.
                # What to use depends on which command was received.
                if mode == on_off.Mode.FAST:
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
                self._set_level(level, mode, reason)

            # For an off command, we need to see if broadcast_done is active.
            # This is a generated broadcast and we need to manually turn the
            # device off so don't update its state until that occurs.
            elif not self.broadcast_done:
                self._set_level(0x00, mode, reason)

        # Starting or stopping manual mode.
        elif on_off.Manual.is_valid(msg.cmd1):
            manual = on_off.Manual.decode(msg.cmd1, msg.cmd2)
            LOG.info("Dimmer %s manual change %s", self.addr, manual)

            self.signal_manual.emit(self, manual, reason)

            # Refresh to get the new level after the button is released.
            if manual == on_off.Manual.STOP:
                self.refresh()

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
          msg (message.InpStandard): The refresh message reply.  The current
              device state is in the msg.cmd2 field.
        """
        LOG.ui("Dimmer %s refresh at level %s", self.addr, msg.cmd2)

        # Update the device dimmer level.
        self._set_level(msg.cmd2, reason=on_off.REASON_REFRESH)

    #-----------------------------------------------------------------------
    def handle_ack(self, msg, on_done, reason=""):
        """Callback for standard commanded messages.

        This callback is run when we get a reply back from one of our
        commands to the device.  If the command was ACK'ed, we know it worked
        so we'll update the internal state of the device and emit the signals
        to notify others of the state change.

        Args:
          msg (message.InpStandard): The reply message from the device.
              The on/off level will be in the cmd2 field.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
        """
        # If this it the ACK we're expecting, update the internal state and
        # emit our signals.
        LOG.debug("Dimmer %s ACK: %s", self.addr, msg)

        _is_on, mode = on_off.Mode.decode(msg.cmd1)
        reason = reason if reason else on_off.REASON_COMMAND
        self._set_level(msg.cmd2, mode, reason)
        on_done(True, "Dimmer state updated to %s" % self._level,
                msg.cmd2)

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
        LOG.debug("Dimmer %s ACK: %s", self.addr, msg)

        # Reason is device because we're simulating a button press.  We
        # can't really pass this around because we just get a broadcast
        # message later from the device.  So we set a temporary variable
        # here and use it in handle_broadcast() to output the reason.
        self.broadcast_reason = reason if reason else on_off.REASON_DEVICE
        on_done(True, "Scene triggered", None)

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
        LOG.debug("Dimmer %s ACK: %s", self.addr, msg)

        # Add the delta and bound at [0, 255]
        level = min(self._level + delta, 255)
        level = max(level, 0)
        self._set_level(level, reason=reason)

        s = "Dimmer %s state updated to %s" % (self.addr, self._level)
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
          addr (Address): The device that sent the message.  This is the
               controller in the scene.
          msg (InpStandard): Broadcast message from the device.  Use
              msg.group to find the group and msg.cmd1 for the command.
        """
        # Make sure we're really a responder to this message.  This shouldn't
        # ever occur.
        entry = self.db.find(addr, msg.group, is_controller=False)
        if not entry:
            LOG.error("Dimmer %s has no group %s entry from %s", self.addr,
                      msg.group, addr)
            return

        reason = on_off.REASON_SCENE

        # Handle on/off commands codes.
        if on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)

            # Get the on level from the database entry.
            level = entry.data[0] if is_on else 0x00
            self._set_level(level, mode, reason=reason)

        # Increment up 1 unit which is 8 levels.
        elif msg.cmd1 == 0x15:
            self._set_level(min(0xff, self._level + 8), reason=reason)

        # Increment down 1 unit which is 8 levels.
        elif msg.cmd1 == 0x16:
            self._set_level(max(0x00, self._level - 8), reason=reason)

        # Starting or stopping manual mode.
        elif on_off.Manual.is_valid(msg.cmd1):
            manual = on_off.Manual.decode(msg.cmd1, msg.cmd2)
            self.signal_manual.emit(self, manual, reason=reason)

            # If the button is released, refresh to get the final level.
            if manual == on_off.Manual.STOP:
                self.refresh()

        else:
            LOG.warning("Dimmer %s unknown group cmd %#04x", self.addr,
                        msg.cmd1)

    #-----------------------------------------------------------------------
    def _set_level(self, level, mode=on_off.Mode.NORMAL, reason=""):
        """Update the device level state.

        This will change the internal state and emit the state changed
        signals.  It is called by whenever we're informed that the device has
        changed state.

        Args:
          level (int): The new device level in the range [0,255].  0 is off.
          mode (on_off.Mode): The type of on/off that was triggered (normal,
               fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
        """
        LOG.info("Setting device %s on=%s %s %s", self.label, level, mode,
                 reason)
        self._level = level

        self.signal_level_changed.emit(self, level, mode, reason)

    #-----------------------------------------------------------------------
