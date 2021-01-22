#===========================================================================
#
# Insteon on/off device
#
#===========================================================================
import enum
import time
from .base import ResponderBase
from ..CommandSeq import CommandSeq
from .. import handler
from .. import log
from .. import message as Msg
from .. import on_off
from .. import util

LOG = log.get_logger()

#Constants for easier comprehension
GROUP_SENSOR = 1
GROUP_RELAY = 2


class IOLinc(ResponderBase):
    """Insteon IOLinc relay/sensor device.

    This class can be used to model the IOLinc device which has a sensor and
    a relay.  Unfortunately, it behaves very poorly.  Unlike every other
    device, it doesn't broadcast the relay and sensor on separate groups.  So
    messages arrive from either and commands are for the relay.  There a
    number of internal mode state which change how the device behaves (see
    below for details).

    NOTE: DO NOT USE THE SET BUTTON ON THE DEVICE TO CONTROL THE DEVICE. This
    will confuse the code and will cause the representation of the sensor
    and relay states to get our of whack.  It will also cause devices which are
    linked to the sensor to react when in fact the sensor has not tripped.
    This can be fixed by running refresh which always updates both the sensor
    and relay.

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).

    NOTES:
      - Broadcast messages from the device always* describe the state of the
        device sensor.
      - Commands sent to the device always affect the state of the relay.
      - Using the On/Off/Set commands will always cause the relay to change
        to the requested state.  The device will ignore any Momentary_A or
        Momentary_C requirements about the type of command or the state of the
        sensor.  Similarly the relay will still trip even if relay_linked is
        enabled and the sensor has not tripped.  The momentary_secs length is
        still respected and the relay will return to the off position after
        the requisite length of time. The code will accururately track the
        state of the relay and sensor following these commands.
      - Controlling the IOLinc from another device or a modem scene works
        as Insteon intended.

    Note about Momentary_C:
        If the IOLinc is in Momentary_C mode and a command
        is sent that does not match the requested sensor state, the relay will
        not trigger.  The code handles this accurately, but a physical device
        will not know the difference.  So, if you click a keypadlinc button, it
        will toggle. The IOLinc may not do anything though - i.e. if the sensor
        is already in that state, it won't fire.  But the keypad button has
        toggled so now it's LED on/off is wrong.  Might be some way to "fix"
        this but it's not obvious whether or not it's a good idea or not.
        Might be nice to have an option to FORCE a controller of the IO linc
        to always be in the correct state to show the door open or closed.

    * Gotchas:
      - Clicking the set button on the device always causes the relay to trip
        and sends a broadcast message containing the state of the relay.  From
        the code, this will appear as a change in the sensor and will be
        recorded as such.
      - The simulated scene function causes basically the same result.  The
        relay will respond to the command, but the device will also send out
        a broadcast message that appears as though it is a change in the sensor
        state.  As such, scene() is not enabled for this device.
    """
    type_name = "io_linc"

    # Map of operating flag values that can be directly set.  Details can
    # be found in document titled 'IOLinc Datasheet'
    class OperatingFlags(enum.IntEnum):
        PROGRAM_LOCK_ON = 0x00
        PROGRAM_LOCK_OFF = 0x01
        LED_ON_DURING_TX = 0x02
        LED_OFF_DURING_TX = 0x03
        RELAY_FOLLOWS_INPUT_ON = 0x04
        RELAY_FOLLOWS_INPUT_OFF = 0x05
        MOMENTARY_A_ON = 0x06
        MOMENTARY_A_OFF = 0x07
        LED_OFF = 0x08
        LED_ENABLED = 0x09
        KEY_BEEP_ENABLED = 0x0a
        KEY_BEEP_OFF = 0x0b
        X10_TX_ON_WHEN_OFF = 0x0c
        X10_TX_ON_WHEN_ON = 0x0d
        INVERT_SENSOR_ON = 0x0e
        INVERT_SENSOR_OFF = 0x0f
        X10_RX_ON_IS_OFF = 0x10
        X10_RX_ON_IS_ON = 0x11
        MOMENTARY_B_ON = 0x12
        MOMENTARY_B_OFF = 0x13
        MOMENTARY_C_ON = 0x14
        MOMENTARY_C_OFF = 0x15

    class Modes(enum.IntEnum):
        LATCHING = 0x00
        MOMENTARY_A = 0x01
        MOMENTARY_B = 0x02
        MOMENTARY_C = 0x03

    def __init__(self, protocol, modem, address, name=None):
        """Constructor

        Args:
          protocol:    (Protocol) The Protocol object used to communicate
                       with the Insteon network.  This is needed to allow
                       the device to send messages to the PLM modem.
          modem:       (Modem) The Insteon modem used to find other devices.
          address:     (Address) The address of the device.
          name         (str) Nice alias name to use for the device.
        """
        super().__init__(protocol, modem, address, name)

        # Used to track the state of sensor and relay
        self._sensor_is_on = False
        self._relay_is_on = False

        # Used to track the momentary_call that will automatically turn off
        # the relay
        self._momentary_call = None

        # Update the group map with the groups to be paired and the handler
        # for broadcast messages from this group
        self.group_map.update({0x01: self.handle_on_off})

        # Define the flags handled by set_flags()
        self.set_flags_map.update({'mode': self.set_mode,
                                   'trigger_reverse': self.set_trigger_reverse,
                                   'relay_linked': self.set_relay_linked,
                                   'momentary_secs': self.set_momentary_secs})

    #-----------------------------------------------------------------------
    @property
    def sensor_is_on(self):
        """Returns the cached sensor state
        """
        return self._sensor_is_on

    #-----------------------------------------------------------------------
    @property
    def relay_is_on(self):
        """Returns the cached relay state
        """
        return self._relay_is_on

    #-----------------------------------------------------------------------
    @property
    def mode(self):
        """Returns the mode from the saved metadata
        """
        meta = self.db.get_meta('IOLinc')
        ret = IOLinc.Modes.LATCHING
        if isinstance(meta, dict) and 'mode' in meta:
            try:
                ret = IOLinc.Modes(meta['mode'])
            except ValueError:
                # Somehow we saved a value that doesn't exist
                pass
        return ret

    #-----------------------------------------------------------------------
    @mode.setter
    def mode(self, val):
        """Saves mode to the database metadata

        Args:
          val:    (IOLinc.Modes)
        """
        if val in IOLinc.Modes:
            meta = {'mode': val.value}
            existing = self.db.get_meta('IOLinc')
            if isinstance(existing, dict):
                existing.update(meta)
                self.db.set_meta('IOLinc', existing)
            else:
                self.db.set_meta('IOLinc', meta)
        else:
            LOG.error("Bad value %s, for mode on IOLinc %s.", val,
                      self.addr)

    #-----------------------------------------------------------------------
    @property
    def trigger_reverse(self):
        """Returns the trigger_reverse state from the saved metadata
        """
        meta = self.db.get_meta('IOLinc')
        ret = False
        if isinstance(meta, dict) and 'trigger_reverse' in meta:
            ret = meta['trigger_reverse']
        return ret

    #-----------------------------------------------------------------------
    @trigger_reverse.setter
    def trigger_reverse(self, val):
        """Saves trigger_reverse state to the database metadata

        Args:
          val:    (bool)
        """
        meta = {'trigger_reverse': val}
        existing = self.db.get_meta('IOLinc')
        if isinstance(existing, dict):
            existing.update(meta)
            self.db.set_meta('IOLinc', existing)
        else:
            self.db.set_meta('IOLinc', meta)

    #-----------------------------------------------------------------------
    @property
    def relay_linked(self):
        """Returns the relay_linked state from the saved metadata
        """
        meta = self.db.get_meta('IOLinc')
        ret = False
        if isinstance(meta, dict) and 'relay_linked' in meta:
            ret = meta['relay_linked']
        return ret

    #-----------------------------------------------------------------------
    @relay_linked.setter
    def relay_linked(self, val):
        """Saves relay_linked state to the database metadata

        Args:
          val:    (bool)
        """
        meta = {'relay_linked': val}
        existing = self.db.get_meta('IOLinc')
        if isinstance(existing, dict):
            existing.update(meta)
            self.db.set_meta('IOLinc', existing)
        else:
            self.db.set_meta('IOLinc', meta)

    #-----------------------------------------------------------------------
    @property
    def momentary_secs(self):
        """Returns the momentary seconds from the saved metadata
        """
        meta = self.db.get_meta('IOLinc')
        ret = 2.0  # the default on the device is 2.0 seconds
        if isinstance(meta, dict) and 'momentary_secs' in meta:
            ret = meta['momentary_secs']
        return ret

    #-----------------------------------------------------------------------
    @momentary_secs.setter
    def momentary_secs(self, val):
        """Saves momentary seconds to the database metadata

        Args:
          val:    (float) .1 - 6300.0
        """
        meta = {'momentary_secs': val}
        existing = self.db.get_meta('IOLinc')
        if isinstance(existing, dict):
            existing.update(meta)
            self.db.set_meta('IOLinc', existing)
        else:
            self.db.set_meta('IOLinc', meta)

    #-----------------------------------------------------------------------
    def get_flags(self, on_done=None):

        """Get the Insteon operational flags field from the device.

        The flags will be passed to the on_done callback as the data field.
        Derived types may do something with the flags by override the
        handle_flags method.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("IOLinc %s cmd: get operation flags", self.label)

        seq = CommandSeq(self.protocol, "IOlinc get flags done", on_done,
                         name="GetFlags")

        # This sends a refresh ping which will respond w/ the current
        # database delta field.  The handler checks that against the
        # current value.  If it's different, it will send a database
        # download command to the device to update the database.
        msg = Msg.OutStandard.direct(self.addr, 0x1f, 0x00)
        msg_handler = handler.StandardCmd(msg, self.handle_flags, on_done)
        seq.add_msg(msg, msg_handler)

        # Get the momentary time value
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00,
                                     bytes([0x00] * 14))
        msg_handler = handler.ExtendedCmdResponse(msg,
                                                  self.handle_get_momentary)
        seq.add_msg(msg, msg_handler)

        seq.run()

    #-----------------------------------------------------------------------
    def set_mode(self, on_done, **kwargs):
        """Set momentary seconds.

        Set the momentary mode

        Args:
          kwargs: Key=value pairs of the flags to change.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # Check for valid input
        mode = util.input_choice(kwargs, 'mode', ['latching', 'momentary_a',
                                                  'momentary_b',
                                                  'momentary_c'])
        if mode is None:
            LOG.error("Invalid mode.")
            on_done(False, 'Invalid mode.', None)
            return

        # Loop through flags, sending appropriate command for each flag
        try:
            mode = IOLinc.Modes[mode.upper()]
        except KeyError:
            mode = IOLinc.Modes.LATCHING
        # Save this to the device metadata
        self.mode = mode
        if mode == IOLinc.Modes.LATCHING:
            type_a = IOLinc.OperatingFlags.MOMENTARY_A_OFF
            type_b = IOLinc.OperatingFlags.MOMENTARY_B_OFF
            type_c = IOLinc.OperatingFlags.MOMENTARY_C_OFF
        elif mode == IOLinc.Modes.MOMENTARY_A:
            type_a = IOLinc.OperatingFlags.MOMENTARY_A_ON
            type_b = IOLinc.OperatingFlags.MOMENTARY_B_OFF
            type_c = IOLinc.OperatingFlags.MOMENTARY_C_OFF
        elif mode == IOLinc.Modes.MOMENTARY_B:
            type_a = IOLinc.OperatingFlags.MOMENTARY_A_ON
            type_b = IOLinc.OperatingFlags.MOMENTARY_B_ON
            type_c = IOLinc.OperatingFlags.MOMENTARY_C_OFF
        elif mode == IOLinc.Modes.MOMENTARY_C:
            type_a = IOLinc.OperatingFlags.MOMENTARY_A_ON
            type_b = IOLinc.OperatingFlags.MOMENTARY_B_ON
            type_c = IOLinc.OperatingFlags.MOMENTARY_C_ON

        seq = CommandSeq(self.protocol, "Set mode complete",
                         on_done, name="SetMode")

        for cmd2 in (type_a, type_b, type_c):
            msg = Msg.OutExtended.direct(self.addr, 0x20, cmd2,
                                         bytes([0x00] * 14))
            callback = self.generic_ack_callback("Mode updated.")
            msg_handler = handler.StandardCmd(msg, callback)
            seq.add_msg(msg, msg_handler)

        seq.run()

    #-----------------------------------------------------------------------
    def set_trigger_reverse(self, on_done, **kwargs):
        """Set momentary seconds.

        Whether the sensor trigger should be reversed.

        Args:
          kwargs: Key=value pairs of the flags to change.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # Check for valid input
        trig_rev = util.input_bool(kwargs, 'trigger_reverse')
        if trig_rev is None:
            LOG.error("Invalid trigger reverse.")
            on_done(False, 'Invalid trigger reverse.', None)
            return

        self.trigger_reverse = trig_rev
        cmd2 = IOLinc.OperatingFlags.INVERT_SENSOR_ON
        if not trig_rev:
            cmd2 = IOLinc.OperatingFlags.INVERT_SENSOR_OFF

        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd2,
                                     bytes([0x00] * 14))
        callback = self.generic_ack_callback("Trigger reverse updated.")
        msg_handler = handler.StandardCmd(msg, callback)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_relay_linked(self, on_done, **kwargs):
        """Set momentary seconds.

        Whether the relay is linked to the sensor state.

        Args:
          kwargs: Key=value pairs of the flags to change.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # Check for valid input
        link_relay = util.input_bool(kwargs, 'relay_linked')
        if link_relay is None:
            LOG.error("Invalid relay linked.")
            on_done(False, 'Invalid relay linked.', None)
            return

        self.relay_linked = link_relay
        cmd2 = IOLinc.OperatingFlags.RELAY_FOLLOWS_INPUT_ON
        if not link_relay:
            cmd2 = IOLinc.OperatingFlags.RELAY_FOLLOWS_INPUT_OFF

        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd2,
                                     bytes([0x00] * 14))
        callback = self.generic_ack_callback("Flags updated.")
        msg_handler = handler.StandardCmd(msg, callback)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_momentary_secs(self, on_done, **kwargs):
        """Set momentary seconds.

        Sets the length of the momentary modes

        Args:
          kwargs: Key=value pairs of the flags to change.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # Check for valid input
        secs = util.input_float(kwargs, 'momentary_secs')
        if secs is None:
            LOG.error("Invalid seconds.")
            on_done(False, 'Invalid seconds.', None)
            return

        # IOLinc allows setting the momentary time between 0.1 and
        # 6300 seconds.  At the low end with a resolution of .1 of a
        # second.  To store the higher numbers, a multiplier is used
        # the multiplier as used by the insteon app has discrete steps
        # 1, 10, 100, 200, and 250.  No other steps are used.
        dec_seconds = int(secs * 10)
        multiple = 0x01
        if dec_seconds > 51000:
            multiple = 0xfa
        elif dec_seconds > 25500:
            multiple = 0xc8
        elif dec_seconds > 2550:
            multiple = 0x64
        elif dec_seconds > 255:
            multiple = 0x0a

        seq = CommandSeq(self.protocol, "Set Momentary Seconds complete",
                         on_done, name="SetMomenSecs")

        time_val = int(dec_seconds / multiple)
        # Set the time value
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00,
                                     bytes([0x00, 0x06, time_val] +
                                           [0x00] * 11))
        callback = self.generic_ack_callback("Flags updated.")
        msg_handler = handler.StandardCmd(msg, callback)
        seq.add_msg(msg, msg_handler)

        # set the multiple
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00,
                                     bytes([0x00, 0x07, multiple, ] +
                                           [0x00] * 11))
        callback = self.generic_ack_callback("Flags updated.")
        msg_handler = handler.StandardCmd(msg, callback)
        seq.add_msg(msg, msg_handler)

        # Save this to the device metadata
        self.momentary_secs = (dec_seconds * multiple) / 10

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

        This will update the state of both the sensor and the relay.

        Args:
          force (bool):  If true, will force a refresh of the device database
                even if the delta value matches as well as a re-query of the
                device model information even if it is already known.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Device %s cmd: status refresh", self.label)

        # NOTE: IOLinc cmd1=0x00 will report the relay state.  cmd2=0x01
        # reports the sensor state which is what we want.
        seq = CommandSeq(self, "Device refreshed", on_done, name="DevRefresh")

        # This sends a refresh ping which will respond w/ the current
        # database delta field.  The handler checks that against the current
        # value.  If it's different, it will send a database download command
        # to the device to update the database.
        # This handles the relay state
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x00)
        msg_handler = handler.DeviceRefresh(self, self.handle_refresh_relay,
                                            force, on_done, num_retry=3)
        seq.add_msg(msg, msg_handler)

        # This Checks the sensor state, ignore force refresh here (we just did
        # it above)
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x01)
        msg_handler = handler.DeviceRefresh(self, self.handle_refresh_sensor,
                                            False, on_done, num_retry=3)
        seq.add_msg(msg, msg_handler)

        # If model number is not known, or force true, run get_model
        self.addRefreshData(seq, force)

        # Run all the commands.
        seq.run()

    #-----------------------------------------------------------------------
    def handle_on_off(self, msg):
        """Handle broadcast messages from this device.

        The broadcast message from a device is sent when the device is
        triggered.  These messages always indicate the state of the sensor.
        With ONE EXCEPTION, if you manually press the set button on the device
        it will toggle the relay and send this message.  This will cause the
        sensor and relay states to be reported wrong.  Just don't use the set
        button.  If you do, you can run refresh to fix the states.

        The message has the group ID in it.  We'll update the
        device state and look up the group in the all link database.  For
        each device that is in the group (as a reponsder), we'll call
        handle_group_cmd() on that device to trigger it.  This way all the
        devices in the group are updated to the correct values when we see
        the broadcast message.

        Args:
          msg (InpStandard):  Broadcast message from the device.
        """
        # If relay_linked is enabled then the relay was triggered
        if self.relay_linked:
            if msg.cmd1 == Msg.CmdType.ON:
                self._set_state(group=GROUP_RELAY, is_on=True)
            elif msg.cmd1 == Msg.CmdType.OFF:
                self._set_state(group=GROUP_RELAY, is_on=False)

        # Pass to Base to handle the sensor state
        super().handle_on_off(msg)

    #-----------------------------------------------------------------------
    def handle_flags(self, msg, on_done):
        """Callback for handling get flag responses.

        This is called when we get a response to the get_flags command.

        Args:
          msg (message.InpStandard):  The refresh message reply.  The current
              device state is in the msg.cmd2 field.
        """
        LOG.ui("Device %s operating flags: %s", self.addr,
               "{:08b}".format(msg.cmd2))

        # Setting latch/A/B/C by hand yields:
        #   76543210  bit numbers
        #   00000010  latching
        #   00001010  MOM A
        #   00011010  MOM B
        #   10011010  MOM C

        # From right to left (bit 0->7).  Values 1/0
        # B0 = program lock 1=on, 0=off
        # B1 = transmit LED 1=on, 0=off
        # B2 = relay linked 1=on, 0=off
        #        if 1, sensor on = relay on
        #              sensor off = relay off
        # B3 = latching 1=off, 1=on
        # B4 = B3=0 & B4=1: momentary B
        # B5 = X10 reversed 1=on, 0=off
        # B6 = trigger reverse 1=on, 0=off
        #        if 1, closed sensor = off
        #        if 0, closed sensor = on
        # B7 = B3=0 & B7=1: momentary C
        # If B3=0, B4=0, B7=0: momentary A
        bits = msg.cmd2
        LOG.ui("Program lock   : %d", util.bit_get(bits, 0))
        LOG.ui("Transmit LED   : %d", util.bit_get(bits, 1))
        LOG.ui("Relay linked   : %d", util.bit_get(bits, 2))
        self.relay_linked = bool(util.bit_get(bits, 2))
        LOG.ui("Trigger reverse: %d", util.bit_get(bits, 6))
        self.trigger_reverse = bool(util.bit_get(bits, 6))
        if not util.bit_get(bits, 3):
            mode = "latching"
        elif util.bit_get(bits, 7):
            mode = "momentary_C"
        elif util.bit_get(bits, 4):
            mode = "momentary_B"
        else:
            mode = "momentary_A"

        # Save mode to device metadata
        self.mode = IOLinc.Modes[mode.upper()]

        LOG.ui("Relay latching : %s", mode)
        on_done(True, "Operation complete", msg.cmd2)

    #-----------------------------------------------------------------------
    def handle_get_momentary(self, msg, on_done):
        """Callback for handling get momemtary time responses.

        This is called when we get a response to the get_flags command.

        Args:
          msg (message.InpExtended):  The extended payload.  The time
              data is in D4.
        """
        # Data Values are:
        # If Data 2 = 1 Rx unit returned data with
        # Data 3:Time multiple (1,10,100, or 250)
        # Data 4:Closure time
        # Data 5:X10 House code(20h = none) In
        # Data 6: X10 Unit In
        # Data 7:House Out
        # Data 8: Unit Out
        # Data 9: S/N

        # Valid momentary times are between .1 and 6300 seconds.  There is
        # finer resolution at the low end and not at much at the high end.

        seconds = (msg.data[3] * msg.data[2]) / 10
        self.momentary_secs = seconds
        LOG.ui("Momentary Secs : %s", seconds)
        on_done(True, "Operation complete", None)

    #-----------------------------------------------------------------------
    def handle_refresh_relay(self, msg):
        """Callback for handling refresh() responses for the relay

        This is called when we get a response to the first refresh() command.
        The refresh command reply will contain the current device relay state
        in cmd2 and this updates the device with that value.  It is called by
        handler.DeviceRefresh when we can an ACK for the refresh command.

        Args:
          msg (message.InpStandard):  The refresh message reply.  The current
              device relay state is in the msg.cmd2 field.
        """
        LOG.ui("IOLinc %s refresh relay on=%s", self.label, msg.cmd2 > 0x00)

        # Current on/off level is stored in cmd2 so update our level to
        # match.
        self._set_state(group=GROUP_RELAY, is_on=msg.cmd2 > 0x00)

    #-----------------------------------------------------------------------
    def handle_refresh_sensor(self, msg):
        """Callback for handling refresh() responses for the sensor.

        This is called when we get a response to the second refresh() command.
        The refresh command reply will contain the current device sensor state
        in cmd2 and this updates the device with that value.  It is called by
        handler.DeviceRefresh when we can an ACK for the refresh command.

        Args:
          msg (message.InpStandard):  The refresh message reply.  The current
              device sensor state is in the msg.cmd2 field.
        """
        LOG.ui("IOLinc %s refresh sensor on=%s", self.label, msg.cmd2 > 0x00)

        # Current on/off level is stored in cmd2 so update our level to
        # match.
        self._set_state(group=GROUP_SENSOR, is_on=msg.cmd2 > 0x00)

    #-----------------------------------------------------------------------
    def handle_ack(self, msg, on_done, reason=""):
        """Callback for standard commanded messages.

        This callback is run when we get a reply back from one of our direct
        commands to the device.  If the command was ACK'ed, we know it worked
        so we'll update the internal state of the device and emit the signals
        to notify others of the state change.

        This overrides the function in SetAndState

        These commands only affect the state of the relay.  They respect the
        momentary_secs length.  However:

        THESE COMMANDS DO NOT RESPECT THE A,B,C NATURE OF THE MOMENTARY MODE

        An on command will always turn the relay on, and an off command
        will always turn the relay off, regardless of the sensor state or how
        the device was linked or the contents of the responder entry Data1

        Args:
          msg (message.InpStandard):  The reply message from the device.
              The on/off level will be in the cmd2 field.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # This state is for the relay.
        LOG.debug("IOLinc %s ACK: %s", self.addr, msg)
        reason = reason if reason else on_off.REASON_COMMAND
        self._set_state(group=GROUP_RELAY, reason=reason,
                        is_on=msg.cmd1 == 0x11)
        on_done(True, "IOLinc command complete", None)

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
            LOG.error("IOLinc %s has no group %s entry from %s", self.addr,
                      msg.group, addr)
            return

        # This reflects a change in the relay state.
        # Handle on/off commands codes.
        if on_off.Mode.is_valid(msg.cmd1):
            is_on = on_off.Mode.decode(msg.cmd1)[0]
            if self.mode == IOLinc.Modes.MOMENTARY_A:
                # In Momentary A the relay only turns on if the cmd matches
                # the responder link D1, else it always turns off.  Even if
                # the momentary time has not elapsed.
                is_on = is_on == bool(entry.data[0])
            elif self.mode == IOLinc.Modes.MOMENTARY_B:
                # In Momentary B, either On or Off will turn on the Relay
                is_on = True
            elif self.mode == IOLinc.Modes.MOMENTARY_C:
                # In Momentary C the relay turns on if the cmd is ON and
                # sensor state matches the responder link D1,
                # OR
                # if the cmd is OFF and the sensor state does not match
                # the responder link D1
                # All other combinations are turn off
                if is_on and bool(entry.data[0]) == self._sensor_is_on:
                    is_on = True
                elif not is_on and bool(entry.data[0]) != self._sensor_is_on:
                    is_on = True
                else:
                    is_on = False
            self._set_state(group=GROUP_RELAY, is_on=is_on,
                            reason=on_off.REASON_SCENE)
        else:
            LOG.warning("IOLinc %s unknown group cmd %#04x", self.addr,
                        msg.cmd1)

#-----------------------------------------------------------------------
    def _cache_state(self, group, is_on, level, reason):
        """Cache the State of the Device

        Used to help with the IOLinc unique functions.

        Args:
          group (int): The group which this applies
          is_on (bool): Whether the device is on.
          level (int): The new device level in the range [0,255].  0 is off.
          reason (str): Reason string to pass around.
        """
        if group == 1:
            self._sensor_is_on = bool(is_on)
        elif group == 2:
            self._relay_is_on = bool(is_on)
            # handle latching and momentary functions
            if is_on and self.mode is not IOLinc.Modes.LATCHING:
                # First remove any pending call, we want to reset the clock
                if self._momentary_call is not None:
                    self.modem.timed_call.remove(self._momentary_call)
                # Set timer to turn relay off after momentary time
                run_time = time.time() + self.momentary_secs
                LOG.info("IOLinc %s delayed relay update in %s seconds",
                         self.label, self.momentary_secs)
                self._momentary_call = \
                    self.modem.timed_call.add(run_time, self._set_state,
                                              False, group=GROUP_RELAY,
                                              reason=reason,
                                              momentary=True)
            elif not is_on and self._momentary_call:
                if self.modem.timed_call.remove(self._momentary_call):
                    LOG.info("IOLinc %s relay off, removing delayed update",
                             self.label)
                self._momentary_call = None

    #-----------------------------------------------------------------------
    def link_data_to_pretty(self, is_controller, data):
        """Converts Link Data1-3 to Human Readable Attributes

        This takes a list of the data values 1-3 and returns a dict with
        the human readable attibutes as keys and the human readable values
        as values.

        Args:
          is_controller (bool):  True if the device is the controller, false
                        if it's the responder.
          data (list[3]):  List of three data values.

        Returns:
          list[3]:  list, containing a dict of the human readable values
        """
        ret = [{'data_1': data[0]}, {'data_2': data[1]}, {'data_3': data[2]}]
        if not is_controller:
            on = 1 if data[0] else 0
            ret = [{'on_off': on},
                   {'data_2': data[1]},
                   {'data_3': data[2]}]
        return ret

    #-----------------------------------------------------------------------
    def link_data_from_pretty(self, is_controller, data):
        """Converts Link Data1-3 from Human Readable Attributes

        This takes a dict of the human readable attributes as keys and their
        associated values and returns a list of the data1-3 values.

        Args:
          is_controller (bool):  True if the device is the controller, false
                        if it's the responder.
          data (dict[3]):  Dict of three data values.

        Returns:
          list[3]:  List of Data1-3 values
        """
        data_1, data_2, data_3 = super().link_data_from_pretty(is_controller,
                                                               data)
        if not is_controller:
            if 'on_off' in data:
                data_1 = 0xFF if data['on_off'] else 0x00
        return [data_1, data_2, data_3]

    #-----------------------------------------------------------------------
