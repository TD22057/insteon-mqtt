#===========================================================================
#
# KeypadLinc Dimmer module
#
#===========================================================================
from ..CommandSeq import CommandSeq
from .. import handler
from .. import log
from .. import message as Msg
from .. import on_off
from .. import util
from .functions import DimmerFuncs
from .KeypadLinc import KeypadLinc

LOG = log.get_logger()


#===========================================================================
class KeypadLincDimmer(DimmerFuncs, KeypadLinc):
    """Insteon KeypadLinc Dimmer Device.

    This class extends the KeypadLinc device to add dimmer functionality.

    This class can be used to model a 6 or 8 button KeypadLinc with dimming
    functionality.  The buttons are numbered 1...8.  In the 6 button, model,
    the top and bottom buttons are combined (so buttons 2 and 7 are unused).
    If the load is detached (meaning button 1 is not controlling the load),
    then a virtual button 9 is used to control the load.

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
        # Here for compatibility purposes can likely be removed eventually.
        self.type_name = "keypad_linc"

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
            if not self.on_off_ramp_supported:
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
        if level is None:
            # If level is not specified it uses the level that the device
            # would go to if the button was physically pressed.
            level = self.derive_on_level(mode)

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
            defaults = [0xff, 0x1f, group]

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
            ramp = 0x1f  # default
            if data[1] in self.ramp_pretty:
                ramp = self.ramp_pretty[data[1]]
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
        LOG.info("KeypadLinc %s manual change %s", self.addr, manual)

        self.signal_manual.emit(self, button=msg.group, manual=manual,
                                reason=reason)

        # Non-load group buttons don't change state in manual mode. (found
        # through experiments)
        if msg.group == self._load_group:
            # Ping the device to get the dimmer states - we don't know
            # what the keypadlinc things the state is - could be on or
            # off.  Doing a dim down for a long time puts all the other
            # devices "off" but the keypadlinc can still think that it's
            # on.  So we have to do a refresh to find out.
            if manual == on_off.Manual.STOP:
                self.refresh()


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
            if is_on and localGroup == self._load_group:
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
