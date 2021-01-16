#===========================================================================
#
# Smartenit EZIO4O - 4 relay output device
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


# EZIOxx Flags settings definition
EZIO4xx_flags = {
    "analog-input": {
        "options": {"none": 0b00000000, "command": 0b00000001,
                    "interval": 0b00000011},
        "mask": 0b00000011,
        "default": "none",
    },
    "alarms": {
        "options": {True: 0b00000100, False: 0b00000000},
        "mask": 0b00000100,
        "default": False,
    },
    "debounce": {
        "options": {True: 0b00001000, False: 0b00000000},
        "mask": 0b00001000,
        "default": False,
    },
    "one-wire": {
        "options": {True: 0b00010000, False: 0b00000000},
        "mask": 0b00010000,
        "default": False,
    },
    "output-timers-unit": {
        "options": {"second": 0b00100000, "minute": 0b00000000},
        "mask": 0b00100000,
        "default": "minute",
    },
    "broadcast-change": {
        "options": {True: 0b01000000, False: 0b00000000},
        "mask": 0b01000000,
        "default": False,
    },
    "output-timers-enable": {
        "options": {True: 0b100000000, False: 0b00000000},
        "mask": 0b10000000,
        "default": False,
    },
}


class EZIO4O(functions.SetAndState, Base):
    """Smartenit EZIO4O - 4 relay output device.

    This class can be used to model the EZIO4O device which has 4 outputs.
    Each output has a normally close and a normally open contact. They are
    independent switches and are controlled via group 1 to group 4 inputs.

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).  Supported signals are:

    - signal_state( Device, int group, bool is_on, on_off.Mode mode, str
                     reason ): Sent whenever an output is turned on or off.
                     Group will be 1 to 4 matching the corresponding device
                     output.
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

        self._is_on = [False, False, False, False]  # output state

        # Support on/off style signals.
        # API: func(Device, int group, bool is_on, on_off.Mode mode,
        #           str reason)
        self.signal_state = Signal()

        # Remote (mqtt) commands mapped to methods calls.  Add to the
        # base class defined commands.
        self.cmd_map.update(
            {
                "set_flags": self.set_flags,
            }
        )

        # EZIOxx configuration port settings. See set_flags().
        self._flag_value = None

        # NOTE: EZIO4O does NOT include the group in the ACK of an on/off
        # command.  So there is no way to tell which output is being ACK'ed
        # if we send multiple messages to it.  Each time on or off is called,
        # it pushes the output to this list so that when the ACK/NAK arrives,
        # we can pop it off and know which output was commanded.
        self._which_output = []

        # Update the group map with the groups to be paired and the handler
        # for broadcast messages from this group
        # The EZIO4O has no inputs and so has no groups to pair to or
        # broadcast messages to process
        # self.group_map.update({})
        self.responder_groups = [1, 2, 3, 4]

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
        LOG.info("EZIO4O %s cmd: status refresh", self.label)

        # NOTE: EZIO4O cmd1=0x4F cmd2=0x02 will report the output state.
        seq = CommandSeq(self.protocol, "Device refreshed", on_done,
                         name="DevRefresh")

        # This sends a refresh ping which will respond w/ the current
        # database delta field.  The handler checks that against the current
        # value.  If it's different, it will send a database download command
        # to the device to update the database.
        msg = Msg.OutStandard.direct(self.addr, 0x4F, 0x02)
        msg_handler = handler.DeviceRefresh(
            self, self.handle_refresh, force, on_done, num_retry=3
        )
        seq.add_msg(msg, msg_handler)

        # If model number is not known, or force true, run get_model
        self.addRefreshData(seq, force)

        # Run all the commands.
        seq.run()

    #-----------------------------------------------------------------------
    def on(self, group=0x01, level=None, mode=on_off.Mode.NORMAL, reason="",
           transition=None, on_done=None):
        """Turn the device on.

        This is a wrapper around the SetAndState functions class.

        Args:
          group (int):  The group to send the command to.
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
        # See __init__ code comments for what this is for.
        self._which_output.append(group)
        super().on(group=group, level=level, mode=mode, reason=reason,
                   transition=transition, on_done=on_done)

    #-----------------------------------------------------------------------
    def off(self, group=0x01, mode=on_off.Mode.NORMAL, reason="",
            transition=None, on_done=None):
        """Turn the device on.

        This is a wrapper around the SetAndState functions class.

        Args:
          group (int):  The group to send the command to.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          transition (int): Transition time in seconds if supported.
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # See __init__ code comments for what this is for.
        self._which_output.append(group)
        super().off(group=group, mode=mode, reason=reason,
                    transition=transition, on_done=on_done)

    #-----------------------------------------------------------------------
    def cmd_on_values(self, mode, level, transition, group):
        """Calculate Cmd Values for On

        Args:
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          level (int): On level between 0-255.
          transition (int): Ramp rate for the transition in seconds.
        Returns
          cmd1, cmd2 (int): Value of cmds for this device.
        """
        if transition or mode == on_off.Mode.RAMP:
            LOG.error("Device %s does not support transition.", self.addr)
            mode = on_off.Mode.NORMAL if mode == on_off.Mode.RAMP else mode
        if level:
            LOG.error("Device %s does not support level.", self.addr)
        cmd1 = 0x45
        cmd2 = group - 1
        return (cmd1, cmd2)

    #-----------------------------------------------------------------------
    def cmd_off_values(self, mode, transition, group):
        """Calculate Cmd Values for Off

        Args:
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          transition (int): Ramp rate for the transition in seconds.
        Returns
          cmd1, cmd2 (int): Value of cmds for this device.
        """
        if transition or mode == on_off.Mode.RAMP:
            LOG.error("Device %s does not support transition.", self.addr)
            mode = on_off.Mode.NORMAL if mode == on_off.Mode.RAMP else mode
        cmd1 = 0x46
        cmd2 = group - 1
        return (cmd1, cmd2)

    #-----------------------------------------------------------------------
    def link_data(self, is_controller, group, data=None):
        """Create default device 3 byte link data.

        This is the 3 byte field (D1, D2, D3) stored in the device database
        entry.  This overrides the defaults specified in base.py for
        specific values used by EZIO4O.

        For controllers, the default fields are:
           D1: unknown (0x00)
           D2: discrete output action (0x00)
           D3: the group number -1 on the local device (0x00)

        For responders, the default fields are:
           D1: unknown (0x00)
           D2: discrete output action (0x00)
           D3: the group number -1 on the local device (0x00)

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

        # Controller data.
        if is_controller:
            defaults = [0x03, 0x00, group]

        # Responder data.
        else:
            defaults = [0x00, 0x00, group - 1]

        # For each field, use the input if not -1, else the default.
        return util.resolve_data3(defaults, data)

    #-----------------------------------------------------------------------
    def link_data_to_pretty(self, is_controller, data):
        """Converts Link Data1-3 to Human Readable Attributes

        This takes a list of the data values 1-3 and returns a dict with
        the human readable attributes as keys and the human readable values
        as values.

        Args:
          is_controller (bool): True if the device is the controller, false
                        if it's the responder.
          data (list[3]): List of three data values.

        Returns:
          list[3]:  list, containing a dict of the human readable values
        """
        if is_controller:
            ret = [{"data_1": data[0]}, {"data_2": data[1]},
                   {"group": data[2]}]
        else:
            ret = [{"data_1": data[0]}, {"data_2": data[1]},
                   {"group": data[2] + 1}]
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
        if "data_1" in data:
            data_1 = data["data_1"]
        data_2 = None
        if "data_2" in data:
            data_2 = data["data_2"]
        data_3 = None
        if "data_3" in data:
            data_3 = data["data_3"]
        if "group" in data:
            if is_controller:
                data_3 = data["group"]
            else:
                data_3 = data["group"] - 1
        return [data_1, data_2, data_3]

    #-----------------------------------------------------------------------
    def set_flags(self, on_done, **kwargs):
        """Set internal device flags.

        This command is used to change EZIOxx Configuration Port settings.
        Valid flags are:
        - analog_input = {none, command, interval}
            Set the analog input options. valid options are:
                none : Analog input is not used (default)
                command : Analog input used, conversion on command
                interval : Analog input used, conversion on fixed interval
            Default = none
        - alarms = {on, off}
            Send Broadcast on Sensor Alarm.
            Default = off
        - debounce = {on, off}
            Send Broadcast on Sensor Alarm.
            Default = off
        - one-wire = {on, off}
            Enable 1-Wire port
            Default = off
        - output-timers-unit = { second, minute }
            Select the output timers unit.
            Default = minute
        - broadcast-change = {on, off}
            Enable broadcast of output and input port change
            Default = 0ff
        - output-timers-enable = {on, off}
            Enable output timers if greater than 0
            Default = off

        Args:
          kwargs: Key=value pairs of the flags to change.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("EZIO4O %s cmd: set flags", self.label)

        # TODO initialize flags on first run
        # Initialise flag value by reading the device Configuration Port
        # settings
        if self._flag_value is None:
            LOG.info(
                "EZIO4O %s cmd: flags not initialized - run get-flags first",
                self.label
            )
            return

        # Check the input flags to make sure only ones we can understand were
        # passed in.
        valid_flags = EZIO4xx_flags.keys()
        flags_to_set = kwargs.keys()

        unknown = set(flags_to_set).difference(valid_flags)
        if unknown:
            LOG.error(
                "EZIO4O Unknown flags input: %s.\n Valid "
                "flags are: %s", unknown, valid_flags
            )

        # Construct the flag register to write
        new_flag_value = self._flag_value

        for field in list(flags_to_set):
            if True in EZIO4xx_flags[field]["options"]:
                option = util.input_bool(kwargs, field)
            else:
                option = util.input_choice(
                    kwargs, field, EZIO4xx_flags[field]["options"].keys()
                )

            if option is not None:
                value = EZIO4xx_flags[field]["options"][option]
                mask = EZIO4xx_flags[field]["mask"]
                new_flag_value = (new_flag_value & ~mask) | (value & mask)
            else:
                raise Exception(
                    "EZIO4O Unknown option: %s for flag: %s.\n Valid "
                    "options are: %s"
                    % (option, field, EZIO4xx_flags[field]["options"].keys())
                )

        # Use a standard message to send "write configuration to port" (0x4D)
        # command
        msg = Msg.OutStandard.direct(self.addr, 0x4D, new_flag_value)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_flags)
        msg_handler = handler.StandardCmd(msg, callback, on_done)

        # Send the message to the PLM modem for protocol.
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def get_flags(self, on_done=None):
        """get internal device flags.

        This command is used to read EZIOxx Configuration Port settings.
        See set_flags() for the settings description

        Args:
          kwargs: Key=value pairs of the flags to change.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("EZIO4O %s cmd: get flags", self.label)

        # Check the input flags to make sure only ones we can understand were
        # passed in.

        # Use a standard message to send "read configuration to port" (0x4E)
        # command
        msg = Msg.OutStandard.direct(self.addr, 0x4E, 0x00)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_flags)
        msg_handler = handler.StandardCmd(msg, callback, on_done)

        # Send the message to the PLM modem for protocol.
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_flags(self, msg, on_done):
        """Callback for flags settings commanded messages.

        This callback is run when we get a reply back from set or read flags
        commands. If the command was ACK'ed, we know it worked so we'll update
        the internal state of flags.

        Args:
          msg (message.InpStandard):  The reply message from the device.
              The on/off level will be in the cmd2 field.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
        """
        assert msg.cmd1 in [0x4D, 0x4E]

        # If this it the ACK we're expecting, update the internal
        # state.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("EZIO4O %s Flag ACK: %s", self.label, msg)
            bits = msg.cmd2
            self._flag_value = bits
            LOG.ui("EZIO4O %s operating flags: %s", self.label,
                   "{:08b}".format(bits))

            for field in EZIO4xx_flags:
                flag_bits = bits & EZIO4xx_flags[field]["mask"]
                option = "unknown"
                flags_opts = EZIO4xx_flags[field]["options"].items()
                for flag_option, option_bits in flags_opts:
                    if flag_bits == option_bits:
                        option = flag_option
                LOG.ui("%s : %s", field, option)

            on_done(True, "EZIO4O %s flags updated" % self.label, None)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("EZIO4O %s flags NAK error: %s", self.label, msg)
            on_done(False, "EZIO4O %s flags update failed" % self.label, None)

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
        LOG.debug("EZIO4O %s refresh response %s", self.label, msg)

        if 0x00 <= msg.cmd2 <= 0x0F:
            for i in range(4):
                is_on = bool(util.bit_get(msg.cmd2, i))

                # State change for output
                if is_on != self._is_on[i]:
                    self._set_state(group=i + 1, is_on=is_on,
                                    reason=on_off.REASON_REFRESH)
        else:
            LOG.error("EZIO4O %s unknown refresh response %s", self.label, msg)

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

        # Get the last output we were commanding.  The message doesn't tell
        # us which output it was so we have to track it here.  See __init__
        # code comments for more info.
        if not self._which_output:
            LOG.error("EZIO4O %s ACK error.  No output ID's were saved",
                      self.label)
        else:
            group = self._which_output.pop(0)

            # Update other groups as reason=refresh
            for i in range(4):
                if i == group - 1:
                    continue
                is_on = bool(util.bit_get(cmd2, i))
                # State change for the output and all outputs with state change
                if is_on != self._is_on[i]:
                    self._set_state(group=i + 1, is_on=is_on,
                                    reason=on_off.REASON_REFRESH)
            # Update the requested group as part of normal set process
            is_on = bool(util.bit_get(cmd2, group))

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
            LOG.error(
                "EZIO4O %s has no group %s entry from %s",
                self.label, msg.group, addr
            )
            return

        # The local button being modified is stored in the db entry.
        localGroup = entry.data[2] + 1

        # Handle on/off commands codes.
        if on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)
            self._set_state(group=localGroup, is_on=is_on, mode=mode,
                            reason=on_off.REASON_SCENE)

        else:
            LOG.warning("EZIO4O %s unknown group cmd %#04x", self.label,
                        msg.cmd1)

    #-----------------------------------------------------------------------
    def _cache_state(self, group, is_on, level, reason):
        """Cache the State of the Device

        Used to help with the EZIO unique functions.

        Args:
          group (int): The group which this applies
          is_on (bool): Whether the device is on.
          level (int): The new device level in the range [0,255].  0 is off.
          reason (str): Reason string to pass around.
        """
        self._is_on[group - 1] = is_on

    #-----------------------------------------------------------------------
