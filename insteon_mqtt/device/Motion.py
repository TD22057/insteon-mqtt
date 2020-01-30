#===========================================================================
#
# Insteon battery powered motion sensor
#
#===========================================================================
from .BatterySensor import BatterySensor
from ..CommandSeq import CommandSeq
from .. import log
from .. import handler
from ..Signal import Signal
from .. import message as Msg
from .. import util

LOG = log.get_logger()


class Motion(BatterySensor):
    """Insteon battery powered motion sensor.

    A motion sensor is an on/off sensor except that it's battery powered and
    only awake when motion is detected or the set button is pressed.

    The issue with a battery powered sensors is that we can't download the
    link database without the sensor being on.  You can trigger the sensor
    manually and then quickly send an MQTT command with the payload 'getdb'
    to download the database.  We also can't test to see if the local
    database is current or what the current motion state is - we can really
    only respond to the sensor when it sends out a message.

    Motion sensors send a Motion.signal_on_off signal (from BatterySensor)
    when motion is detected.  Some motion sensors also support a dusk/dawn
    light sensor.  In that case, the Motion.signal_dawn signal is emitted
    when the light sensor changes state.

    The device will broadcast messages on the following groups:
      group 01 = on (0x11) / off (0x13)
      group 02 = dusk/dawn light sensor
      group 03 = low battery (0x11) / good battery (0x13)
      group 04 = heartbeat (0x11)

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).  Supported signals are:

    - signal_on_off( Device, bool is_on ): Sent when the sensor is tripped
      (is_on=True) or resets (is_on=False).

    - signal_low_battery( Device, bool is_low ): Sent to indicate the current
      battery state.

    - signal_heartbeat( Device, True ): Sent when the device has broadcast a
      heartbeat signal.

    - signal_dawn( Device, bool is_dawn): Sent when the device indicates that
      the light level (dusk/dawn) has changed.  Not all motion sensors support
      this.
    """
    def __init__(self, protocol, modem, address, name=None):
        """Constructor

        Args:
          protocol (Protocol):  The Protocol object used to communicate
                   with the Insteon network.  This is needed to allow the
                   device to send messages to the PLM modem.
          modem (Modem):  The Insteon modem used to find other devices.
          address (Address): The address of the device.
          name (str):  Nice alias name to use for the device.
        """
        super().__init__(protocol, modem, address, name)

        self.signal_dawn = Signal()  # (Device, bool is_dawn)

        # Insert the dawn/dusk callback on group 02.  Base class already
        # handles the other groups.
        self.group_map[0x02] = self.handle_dawn

        # Remote (mqtt) commands mapped to methods calls.  Add to the
        # base class defined commands.
        self.cmd_map.update({
            'set_flags' : self.set_flags,
            })

        # Set default values for bits.  These should always be updated prior
        # to setting
        self.led_on = 1
        self.night_only = 0
        self.on_only = 0

    #-----------------------------------------------------------------------
    def handle_dawn(self, msg):
        """Handle a dusk/dawn message.

        This is called by the BatterySensor base class when a group broadcast
        on group 02 is sent out by the sensor.  Not all devices support the
        the light sensor so this may never happen.

        Args:
          msg (InpStandard):  Broadcast message from the device.

        """
        # Send True for dawn, False for dusk.
        self.signal_dawn.emit(self, msg.cmd1 == 0x11)

    #-----------------------------------------------------------------------
    def set_flags(self, on_done, **kwargs):
        """Set internal device flags.

        This command is used to change internal device flags and states.
        These include LED On/Off (off conserves batteries), Timeout (seconds
        between state updates), Light Sensitivity (Percentage of light for
        night sensitivity), Night Only Mode and On Only Mode:

        valid kwargs:
        - led_on = 1/0: Should led flash on motion?

        - night_only = 1/0: Should motion only be reported at night?

        - on_only = 1/0: Should only on motions be reported?

        - timeout = seconds between state updates (30 second increments, 2842
        models allow between 30 seconds to over 4 hours, the 2844 models allow
        between 30 seconds and 40 minutes)

        - light_sensitivity = 1-255:  Amount of darkness required for night
        to be triggered.

        Args:
          kwargs: Key=value pairs of the flags to change.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Motion %s cmd: set operation flags", self.label)

        # Check the input flags to make sure only ones we can understand were
        # passed in.
        flags = set(["led_on", "night_only", "on_only", "timeout",
                     "light_sensitivity"])
        unknown = set(kwargs.keys()).difference(flags)
        if unknown:
            raise Exception("Unknown Motion flags input: %s.\n Valid flags "
                            "are: %s" % unknown, flags)

        seq = CommandSeq(self.protocol, "Flags set", on_done)

        # For some flags we need to know the existing bit before we change it.
        # So to insure that we are starting from the correct values, get the
        # current bits and pass that to the callback which will update them to
        # make the changes.
        flags = set(["led_on", "night_only", "on_only"])
        if any(x in kwargs.keys() for x in flags):
            seq.add(self._get_ext_flags)
            seq.add(self._change_flags, kwargs)
        if "light_sensitivity" in kwargs.keys():
            seq.add(self._set_light_sens, kwargs["light_sensitivity"])
        if "timeout" in kwargs.keys():
            seq.add(self._set_timeout, kwargs["timeout"])

        seq.run()

    #-----------------------------------------------------------------------
    def _change_flags(self, flags, on_done):
        """Change the operating flags.

        See the set_flags() code for details.
        """

        # Generate the value of the combined flags.
        value = 0
        value = util.bit_set(value, 3, flags.get("led_on", self.led_on))
        value = util.bit_set(value, 2,
                             flags.get("night_only", self.night_only))
        value = util.bit_set(value, 1, flags.get("on_only", self.on_only))

        # Push the flags value to the device.
        data = bytes([
            0x00,   # D1 = 0x00
            0x05,   # D2 = 0x05 Set Flags
            value,  # D3 = the flag value
            ] + [0x00] * 11)
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)
        msg_handler = handler.StandardCmd(msg, self.handle_ext_cmd)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def _get_ext_flags(self, on_done=None):
        """Get the Insteon operational extended flags field from the device.

        For the motion device, these flags include led_on, night_only, and
        on_only.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Motion %s cmd: get extended operation flags", self.label)

        # Requesting data is all 0s. Flags are in D6 of ext response msg
        data = bytes([0x00] * 14)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)
        msg_handler = handler.ExtendedCmdResponse(msg, self.handle_ext_flags,
                                                  on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_ext_flags(self, msg, on_done):
        """Handle replies to the _get_ext_flags command.

        Data 6 of the extended response contains the bits we are interested
        in.  This parses them out and stores their value for use in setting
        flags.

        Args:
          msg (message.InpExtended):  The message reply.  The current
              flags are in D6.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
        """
        LOG.ui("Motion %s extended operating flags: %s", self.addr,
               "{:08b}".format(msg.data[5]))
        self.led_on = util.bit_get(msg.data[5], 3)
        self.night_only = util.bit_get(msg.data[5], 2)
        self.on_only = util.bit_get(msg.data[5], 1)
        on_done(True, "Operation complete", msg.data[5])

    #-----------------------------------------------------------------------
    def handle_ext_cmd(self, msg, on_done):
        """Handle replies to the set_flags command.
        Nothing to do, any NAK of failure is caught by the message handler
        """
        on_done(True, "Operation complete", None)

    #-----------------------------------------------------------------------
    def _set_light_sens(self, sensitivity, on_done):
        """Change the light sensitivity amount.

        See the set_flags() code for details.
        """
        assert 1 <= int(sensitivity) <= 255

        # Push the flags value to the device.
        data = bytes([
            0x00,   # D1 = 0x00
            0x04,   # D2 = 0x05 Set Flags
            int(sensitivity),  # D3 = the sensitivity value
            ] + [0x00] * 11)
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)
        msg_handler = handler.StandardCmd(msg, self.handle_ext_cmd)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def _set_timeout(self, timeout, on_done):
        """Change the timeout in seconds.

        This will automatically change the timeout requested to fit within the
        valid values.

        See the set_flags() code for details.
        """
        timeout = int(timeout)
        # 30 seconds is the minimum permitted timeout
        if timeout < 30:
            timeout = 30
        # The calculation of the timeout value is stored differently on the
        # older 2842 and the newer 2844 motion sensors.  We will assume the
        # newer style as a default.
        if (self.db.desc is not None and
                self.db.desc.model.split("-")[0] == "2842"):
            # Max 4 hours
            if timeout > 14400:
                timeout = 14400
            timeout = int(timeout / 30) - 1
            LOG.ui("Motion %s setting timeout to %s seconds", self.addr,
                   ((timeout + 1) * 30))
        else:
            # Assuming this is a 2844 sensor or that is uses the same style
            # Max 40 Minutes
            if timeout > 2400:
                timeout = 2400
            timeout = int(timeout / 10)
            LOG.ui("Motion %s setting timeout to %s seconds", self.addr,
                   ((timeout) * 10))

        # Push the flags value to the device.
        data = bytes([
            0x00,   # D1 = 0x00
            0x03,   # D2 = 0x05 Set Flags
            timeout,  # D3 = the sensitivity value
            ] + [0x00] * 11)
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)
        msg_handler = handler.StandardCmd(msg, self.handle_ext_cmd)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
