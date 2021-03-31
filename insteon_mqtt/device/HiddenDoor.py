#===========================================================================
#
# Insteon battery powered hidden door sensor
#
#===========================================================================
import functools
import time
from .BatterySensor import BatterySensor
from .. import log
from .. import handler
from ..Signal import Signal
from .. import message as Msg
from .. import on_off
from .. import util

LOG = log.get_logger()


class HiddenDoor(BatterySensor):
    """Insteon battery powered hidden sensor.

    A hidden door sensor is basically an on/off sensor except that it's
    battery powered and only awake for a short time after open or closed is
    detected or the set button is pressed.

    It can be configured in "one group" mode or "two group" mode:

    In one group mode the open is broadcast as on ON command to group 0x01
    and closed state is broadcast as an OFF command to group 0x01

    In two group mode, open is broadcast as an ON command to group 0x01 and
    closed is broadcast as on ON command to group 0x02

    This was done to allow direct automation links from this device to
    operate different devices for open and closed.

    The hidden door sensor also supports low battery on group 0x03.  This
    is sent when the battery level falls below a configurable low battery
    level.

    This sensor will also broadcast a heartbeat signal on group 4.  The
    default interval for heartbeat is 24 hours but it is configurable in 5
    minute increments from 5 mins to 24 hours.

    5 mins x 0x00->0xff

    Details on this device are in the insteon developers notes here:

    http://cache.insteon.com/developer/2845-222dev-102013-en.pdf

    The issue with a battery powered sensor is that we can't download the
    link database without the sensor being on.  You can trigger the sensor
    manually and then quickly send an MQTT command with the payload 'getdb'
    to download the database.  We also can't test to see if the local
    database is current or what the current open/closed state is - we can
    really only respond to the sensor when it sends out a message.

    The device will broadcast messages on the following groups:
      group 01 = Open [One or Two Group Mode] (0x11) / Closed [One Group
      Mode Only] (0x13)
      group 02 = Closed [Two Group Mode Only] (0x11)
      group 03 = Low battery (0x11) / Good battery (0x13)
      group 04 = Heartbeat (0x11)

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).  Supported signals are:

    - signal_on_off( Device, bool is_on ): Sent when the sensor is tripped
      (is_on=True) or resets (is_on=False).

    - signal_low_battery( Device, bool is_low ): Sent to indicate the current
      battery state.

    - signal_heartbeat( Device, True ): Sent when the device has broadcast a
      heartbeat signal.
    """
    type_name = "hidden_door"

    # This defines what is the minimum time between battery status requests
    # for devices that support it.  Value is in seconds
    # Currently set at 3 hours
    BATTERY_TIME = (60 * 60) * 3

    def __init__(self, protocol, modem, address, name=None, config_extra=None):
        """Constructor

        Args:
          protocol (Protocol):  The Protocol object used to communicate
                   with the Insteon network.  This is needed to allow the
                   device to send messages to the PLM modem.
          modem (Modem):  The Insteon modem used to find other devices.
          address (Address): The address of the device.
          name (str):  Nice alias name to use for the device.
          config_extra (dict): Extra configuration settings
        """
        super().__init__(protocol, modem, address, name, config_extra)

        self.signal_voltage = Signal()

        # Insert the 'Two Groups' closed callback on group 02.  Base class
        # already handles the other groups.
        self.group_map.update({0x02 : self.handle_closed})

        # Remote (mqtt) commands mapped to methods calls.  Add to the
        # base class defined commands.
        self.cmd_map.update({
            'set_heart_beat_interval': self.set_heart_beat_interval,
            'set_low_battery_voltage': self.set_low_battery_voltage,
            'get_battery_voltage' : self.get_flags,
            })

        # This allows for a short timer between sending automatic battery
        # requests.  Otherwise, a request may get queued multiple times
        self._battery_request_time = 0

        # Define the flags handled by set_flags()
        # Keys are the flag names in lower case.  The value should be the
        # function to call.  The signature of the function is
        # function(on_done=None, **kwargs).  Each function will receive all
        # flags specified in the call and should just ignore those that are
        # unrelated.  If the value None is used, no function will be called if
        # that key is the only one passed.  Functions will only be called once
        # even if the same function is used for multiple flags
        self.set_flags_map = {"cleanup_report": self._set_cleanup_report,
                              "led_disable": self._set_led_disable,
                              "link_to_all": self._set_link_to_all,
                              "two_groups": self._set_two_groups,
                              "prog_lock": self._set_prog_lock,
                              "repeat_closed": self._set_repeat_closed,
                              "repeat_open": self._set_repeat_open,
                              "stay_awake": self._set_stay_awake}

    #-----------------------------------------------------------------------
    @property
    def battery_voltage_time(self):
        """Returns the timestamp of the last battery voltage report from the
        saved metadata
        """
        ret = self.db.get_meta('battery_voltage_time')
        if ret is None:
            ret = 0
        return ret

    #-----------------------------------------------------------------------
    @battery_voltage_time.setter
    def battery_voltage_time(self, val):
        """Saves the timestamp of the last battery voltage report to the
        database metadata
        Args:
          val:    (timestamp) time.time() value
        """
        self.db.set_meta('battery_voltage_time', val)

    #-----------------------------------------------------------------------
    def set_low_battery_voltage(self, on_done, voltage=None):
        """Set low voltage value.

        Called from the mqtt command functions or cmd_line

        Args:
          voltage: (int) The low voltage value
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        voltage = util.input_byte({'voltage': voltage}, 'voltage')
        if voltage is not None:
            LOG.info("Hidden Door %s cmd: set low voltage= %s", self.label,
                     voltage)
            on_done(True, "Low voltage set.", None)
        else:
            LOG.warning("Hidden Door %s set_low_voltage cmd requires voltage \
                         key.", self.label)
            on_done(False, "Low voltage not specified.", None)
            return

        # Extended message data - see hidden door dev guide page 10
        data = bytes([
            0x01,   # D1 must be group 0x01
            0x03,   # D2 set low bat voltage
            voltage,  # D3 voltage
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_low_battery_voltage,
                                     voltage=voltage)
        msg_handler = handler.StandardCmd(msg, callback, on_done)

        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_heart_beat_interval(self, on_done, interval=None):
        """Set heart beat interval.

        Called from the mqtt command functions or cmd_line

        Args:
          voltage: (float) The low voltage value
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        interval = util.input_byte({'interval': interval}, 'interval')
        if interval is not None:
            LOG.info("Hidden Door %s cmd: set heart beat interval= %s",
                     self.label, interval)
            on_done(True, "heart Beat Interval set.", None)
        else:
            LOG.warning("Hidden Door %s heart_beat_interval cmd requires \
                        interval key.", self.label)
            on_done(False, "Interval not specified.", None)
            return

        # Extended message data - see hidden door dev guide page 10
        data = bytes([
            0x01,   # D1 must be group 0x01
            0x02,   # D2 set heart beat interval
            interval,  # D3 interval
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_heart_beat_interval,
                                     interval=interval)
        msg_handler = handler.StandardCmd(msg, callback, on_done)

        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_closed(self, msg):
        """Handle sensor activation.

        This is called by the device when a group broadcast on group 02 is
        sent out by the sensor.

        This is necessary because an ON command on this group actually means
        that this device is off or closed.  Otherwise this is copied from
        Base.handle_on_off()

        Args:
          msg (InpStandard):  Broadcast message from the device.
        """
        # If we have a saved reason from a simulated scene command, use that.
        # Otherwise the device button was pressed.
        reason = self.broadcast_reason if self.broadcast_reason else \
                 on_off.REASON_DEVICE
        self.broadcast_reason = ""

        # On/off command codes.
        if on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)
            LOG.info("Device %s broadcast grp: %s on: %s mode: %s", self.addr,
                     msg.group, is_on, mode)

            if is_on:
                # Note is_on value is inverted in call to _set_state
                level = self.derive_on_level(mode)
                self._set_state(is_on=False, level=level, mode=mode,
                                group=msg.group, reason=reason)
            else:
                level = self.derive_off_level(mode)
                self._set_state(is_on=True, level=level, mode=mode,
                                group=msg.group, reason=reason)

        # This will find all the devices we're the controller of for this
        # group and call their handle_group_cmd() methods to update their
        # states since they will have seen the group broadcast and updated
        # (without sending anything out).
        self.update_linked_devices(msg)

    #-----------------------------------------------------------------------
    def get_flags(self, on_done=None):
        """Get the Insteon operational extended flags field from the device.

        For the hidden door device, these flags include cleanup_report,
        led_disable, link_to_all, two_groups, prog_lock, repeat_closed,
        repeat_open, as well as the battery voltage, heart beat interval,
        low battery level

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Hidden Door %s cmd: get extended operation flags",
                 self.label)

        # Requesting data is all 0s. Flags are in D3 of ext response msg
        data = bytes([0x00] * 14)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)
        msg_handler = handler.ExtendedCmdResponse(msg, self.handle_ext_flags,
                                                  on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_ext_flags(self, msg, on_done):
        """Handle replies to the get_flags command.

        Data 3 contains the operating flags
        Data 4 contains the battery voltage
        Data 5 open/closed status
        Data 6 heart beat interval
        Data 7 low battery level

        Args:
          msg (message.InpExtended):  The message reply.  The current
              flags are in D2.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
        """
        LOG.ui("Hidden door sensor %s extended operating flags: %s", self.addr,
               "{:08b}".format(msg.data[2]))

        # Decode and display the operating flags
        rawflags = msg.data[2]
        LOG.ui("Hidden door sensor %s Configuration:", self.addr)
        # Bit 0
        if rawflags & 0b00000001 == 1:
            LOG.ui("\tSend Cleanup Report")
        else:
            LOG.ui("\tDon't Send Cleanup Report")
        # Bit 1
        if rawflags & 0b00000010 == 2:
            LOG.ui("\tSend Open on Group 1 ON and Closed on Group 2 ON")
        else:
            LOG.ui("\tSend both Open and Closed on Group 1 [On=Open and "
                   "Off=Closed]")
        # Bit 2
        if rawflags & 0b00000100 == 4:
            LOG.ui("\tSend Repeated Open Commands [Every 5 mins for 50 mins]")
        else:
            LOG.ui("\tDon't Send Repeated Open Commands")
        # Bit 3
        if rawflags & 0b00001000 == 8:
            LOG.ui("\tSend Repeated Closed Commands [Every 5 mins for 50 "
                   "mins]")
        else:
            LOG.ui("\tDon't Send Repeated Closed Commands")
        # Bit 4
        if rawflags & 0b00010000 == 16:
            LOG.ui("\tLink to FF Group")
        else:
            LOG.ui("\tDon't link to FF Group")
        # Bit 5
        if rawflags & 0b00100000 == 32:
            LOG.ui("\tLED does not blink on transmission")
        else:
            LOG.ui("\tLED blinks on transmission")
        # Bit 6
        if rawflags & 0b01000000 == 64:
            LOG.ui("\tNo Effect")
        else:
            LOG.ui("\tNo Effect")
        # Bit 7
        if rawflags & 0b10000000 == 128:
            LOG.ui("\tProgramming lock on")
        else:
            LOG.ui("\tProgramming lock off")

        # D6 Heart Beat Interval
        # 5 minute increments for 1-255.  0 = 24 hours (default)
        hb_interval = msg.data[5]
        if hb_interval > 0:
            hb_interval_minutes = hb_interval * 5
        else:
            hb_interval_minutes = 24 * 60  # convert 24 hours to minutes
        LOG.ui("\tHeart beat interval raw level is %s or %s minutes ",
               hb_interval, hb_interval_minutes)

        # D7 Low Battery Level
        lb_level = msg.data[6]
        LOG.ui("\tLow battery level is %s", lb_level)

        # D4 Current Battery Level
        batt_volt = msg.data[3]
        LOG.ui("Hidden door sensor %s Battery voltage is %s", self.addr,
               batt_volt)

        self.battery_voltage_time = time.time()

        self.signal_voltage.emit(self, batt_volt)

        on_done(True, "Operation complete", msg.data[5])

    #-----------------------------------------------------------------------
    def handle_ext_cmd(self, msg, on_done):
        """Handle replies to the set_flags command.
        Nothing to do, any NAK of failure is caught by the message handler
        """
        on_done(True, "Operation complete", None)

    #-----------------------------------------------------------------------
    def handle_low_battery_voltage(self, msg, on_done, voltage):
        """Callback for handling set_low_battery_voltage() responses.

        This is called when we get a response to the
        set_low_battery_voltage() command. Update stored low bat voltage in
        device DB and call the on_done callback with the status.

        Args:
          msg (InpStandard): The response message from the command.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        on_done(True, "Low Battery Voltage", None)

    #-----------------------------------------------------------------------
    def handle_heart_beat_interval(self, msg, on_done, interval):
        """Callback for handling set_heart_beat_interval() responses.

        This is called when we get a response to the
        set_heart_beat_interval() command. Update stored heart beat interval
        in device DB and call the on_done callback with the status.

        Args:
          msg (InpStandard): The response message from the command.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        on_done(True, "Heart Beat Interval", None)

    #-----------------------------------------------------------------------
    def _set_cleanup_report(self, on_done=None, **kwargs):
        """Set clean up report on

        - cleanup_report = 1/0: tell the device whether or not to send
        cleanup reports
        """
        # Check for valid input
        cleanup_report = util.input_bool(kwargs, 'cleanup_report')
        if cleanup_report is None:
            on_done(False, 'Invalid cleanup_report flag.', None)
            return

        # The dev guide says 0x17 for cleanup report on and 0x16 for off
        cmd = 0x17 if cleanup_report else 0x16
        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd,
                                     bytes([0x00] * 14))

        msg_handler = handler.StandardCmd(msg, self.handle_ext_cmd,
                                          on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def _set_led_disable(self, on_done=None, **kwargs):
        """Set LED Disable - LED near back of device will light momentarily
           when changing state

        - led_disable = 1/0: disables small led on back of device to blink
        on state change

        """
        # Check for valid input
        led_disable = util.input_bool(kwargs, 'led_disable')
        if led_disable is None:
            on_done(False, 'Invalid led_disable flag.', None)
            return

        # The dev guide says 0x02 for LED disable and 0x03 for enable
        cmd = 0x02 if led_disable else 0x03
        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd,
                                     bytes([0x00] * 14))

        msg_handler = handler.StandardCmd(msg, self.handle_ext_cmd,
                                          on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def _set_link_to_all(self, on_done=None, **kwargs):
        """Set Link to all - This creates a link to the 0xFF group, which is
           is the same as link to your modem on groups
           0x01, 0x02, 0x03, 0x04

        - link_to_all = 1/0: links to 0xFF group (all available groups)
        """
        # Check for valid input
        link_to_all = util.input_bool(kwargs, 'link_to_all')
        if link_to_all is None:
            on_done(False, 'Invalid link_to_all flag.', None)
            return

        # The dev guide says 0x06 for link to all and 0x07 for link to one
        cmd = 0x06 if link_to_all else 0x07
        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd,
                                     bytes([0x00] * 14))

        msg_handler = handler.StandardCmd(msg, self.handle_ext_cmd,
                                          on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def _set_prog_lock(self, on_done=None, **kwargs):
        """Set local programming lock

        - prog_lock = 1/0: prevents device from being programmed by local
        button presses
        """
        # Check for valid input
        prog_lock = util.input_bool(kwargs, 'prog_lock')
        if prog_lock is None:
            on_done(False, 'Invalid prog_lock flag.', None)
            return

        # The dev guide says 0x00 for locl on and 0x01 for lock off
        cmd = 0x00 if prog_lock else 0x01
        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd,
                                     bytes([0x00] * 14))

        msg_handler = handler.StandardCmd(msg, self.handle_ext_cmd,
                                          on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def _set_repeat_closed(self, on_done=None, **kwargs):
        """Set Repeat Closed - This sets the device to send repeated closed
           messages every 5 mins for 50 mins

        - repeat_closed = 1/0: Repeat open command every 5 mins for 50 mins
        """
        # Check for valid input
        repeat_closed = util.input_bool(kwargs, 'repeat_closed')
        if repeat_closed is None:
            on_done(False, 'Invalid repeat_closed flag.', None)
            return

        # The dev guide says 0x08 for repeat closed and 0x09 for don't
        # repeat closed
        cmd = 0x08 if repeat_closed else 0x09
        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd,
                                     bytes([0x00] * 14))

        msg_handler = handler.StandardCmd(msg, self.handle_ext_cmd,
                                          on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def _set_repeat_open(self, on_done=None, **kwargs):
        """Set Repeat Open - This sets the device to send repeated open
           messages every 5 mins for 50 mins

        - repeat_open = 1/0: Repeat open command every 5 mins for 50 mins
        """
        # Check for valid input
        repeat_open = util.input_bool(kwargs, 'repeat_open')
        if repeat_open is None:
            on_done(False, 'Invalid repeat_open flag.', None)
            return

        # The dev guide says 0x0A for repeat open and 0x0B for don't
        # repeat open
        cmd = 0x0a if repeat_open else 0x0b
        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd,
                                     bytes([0x00] * 14))

        msg_handler = handler.StandardCmd(msg, self.handle_ext_cmd,
                                          on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def _set_stay_awake(self, on_done=None, **kwargs):
        """Set Stay Awake - Do not go to sleep

        - stay_awake = 1/0: keeps device awake - but uses a lot of battery
        """
        # Check for valid input
        stay_awake = util.input_bool(kwargs, 'stay_awake')
        if stay_awake is None:
            on_done(False, 'Invalid stay_awake flag.', None)
            return

        # The dev guide says 0x0A for repeat open and 0x0B for don't
        # repeat open
        cmd = 0x18 if stay_awake else 0x19
        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd,
                                     bytes([0x00] * 14))

        msg_handler = handler.StandardCmd(msg, self.handle_ext_cmd,
                                          on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def _set_two_groups(self, on_done=None, **kwargs):
        """Set Two Groups

        - two_groups = 1/0: Report open/close on group 1 or report open on
        group 1 and closed on 2
        """
        # Check for valid input
        two_groups = util.input_bool(kwargs, 'two_groups')
        if two_groups is None:
            on_done(False, 'Invalid two_groups flag.', None)
            return

        # The dev guide says 0x04 sets two groups and 0x05 sets one group
        cmd = 0x04 if two_groups else 0x05
        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd,
                                     bytes([0x00] * 14))

        msg_handler = handler.StandardCmd(msg, self.handle_ext_cmd,
                                          on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def auto_check_battery(self):
        """Queues a Battery Voltage Request if Necessary

        If the requisite amount of time has elapsed, queue a battery request.
        """

        # This is a device that supports battery requests
        last_checked = self.battery_voltage_time
        # Don't send this message more than once every 5 minutes no
        # matter what
        if (last_checked + self.BATTERY_TIME <= time.time() and
                self._battery_request_time + 300 <= time.time()):
            self._battery_request_time = time.time()
            LOG.info("Hidden Door %s: Auto requesting battery voltage",
                     self.label)
            self.get_flags()

    #-----------------------------------------------------------------------
    def awake(self, on_done):
        """Injects a Battery Voltage Request if Necessary

        Queue a battery request that should go out now, since the device is
        awake.
        """
        self.auto_check_battery()
        super().awake(on_done)

    #-----------------------------------------------------------------------
    def _pop_send_queue(self):
        """Injects a Battery Voltage Request if Necessary

        Queue a battery request that should go out now, since the device is
        awake.
        """
        self.auto_check_battery()
        super()._pop_send_queue()

    #-----------------------------------------------------------------------
