#===========================================================================
#
# Thermostat module
#
#===========================================================================
import enum
from .Base import Base
from ..CommandSeq import CommandSeq
from .. import log
from .. import message as Msg
from .. import handler
from .. import util
from ..Signal import Signal

LOG = log.get_logger()


class Thermostat(Base):
    """Insteon Thermostat

    This works with the 2441TH line of Insteon Thermostats.  It will not work
    with the older Venstar Thermostats.

    The Thermostat 'broadcasts' alerts for a series of conditions using
    different broadcast group and direct messages.  This requires pairing the
    modem as a responder for all of the groups that the Thermostat uses.  The
    pair() method will do this automatically after the Thermostat is set as a
    responder to the modem (set modem, then Thermostat).

    When the thermostat alert is triggered, it will emit a signal using
    Thermostat.signal_*.

    Sample configuration input:

        insteon:
          devices:
            - thermostat:
              address: 44.a3.79

    """

    # broadcast group ID alert description
    class Groups(enum.IntEnum):
        COOLING = 0x01
        HEATING = 0x02
        HUMID_HIGH = 0x03
        HUMID_LOW = 0x04
        BROADCAST = 0xEF

    # Mapping of fan states
    class Fan(enum.IntEnum):
        AUTO = 0x00
        ON = 0x01

    # Irritatingly, this mapping is not consistent anywhere.
    # Insteon loves to be irritating like that.
    class Mode(enum.IntEnum):
        OFF = 0x00
        AUTO = 0x01
        HEAT = 0x02
        COOL = 0x03
        PROGRAM = 0x04

    class ModeCommands(enum.IntEnum):
        OFF = 0x09
        HEAT = 0x04
        COOL = 0x05
        AUTO = 0x06
        PROGRAM = 0x0a

    class Status(enum.Enum):
        OFF = "OFF"
        HEATING = "HEATING"
        COOLING = "COOLING"

    class FanCommands(enum.IntEnum):
        ON = 0x07
        AUTO = 0x08

    class HoldCommands(enum.IntEnum):
        OFF = 0x00
        TEMP = 0x01

    # A few constants to make thing easier to read
    FARENHEIT = 0
    CELSIUS = 1

    def __init__(self, protocol, modem, address, name=None):
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
        # Set default values to attributes, may be overwritten by saved values
        super().__init__(protocol, modem, address, name)

        self.cmd_map.update({
            'get_status' : self.get_status
            })

        self.signal_ambient_temp_change = Signal()  # emit(device, int temp_c)
        self.signal_fan_mode_change = Signal()  # emit(device, Fan fan_mode)
        self.signal_mode_change = Signal()  # emit(device, Mode mode)
        self.signal_cool_sp_change = Signal()  # emit(device, int cool_sp in c)
        self.signal_heat_sp_change = Signal()  # emit(device, int heat_sp in c)
        self.signal_ambient_humid_change = Signal()  # emit(device, int humid)
        self.signal_status_change = Signal()  # emit(device, Status status)
        self.signal_hold_change = Signal()  # emit(device, bool)
        self.signal_energy_change = Signal()  # emit(device, bool)

        # Add handler for processing direct Messages from the thermostat.
        # This handler stays active for all time - it never ends.
        protocol.add_handler(handler.ThermostatCmd(self))

        # Defined controller groups and the handlers for them
        self.group_map = {
            self.Groups.COOLING.value: self.handle_message,
            self.Groups.HEATING.value: self.handle_message,
            self.Groups.HUMID_HIGH.value: self.handle_message,
            self.Groups.HUMID_LOW.value: self.handle_message,
            self.Groups.BROADCAST.value: self.handle_message,
            self.Groups.COOLING.value: self.handle_message,
            self.Groups.COOLING.value: self.handle_message
            }

    @property
    def units(self):
        """Returns the units from the saved metadata
        """
        meta = self.db.get_meta('thermostat')
        ret = Thermostat.FARENHEIT
        if isinstance(meta, dict) and 'units' in meta:
            ret = meta['units']
        return ret

    @units.setter
    def units(self, val):
        """Saves units to the database metadata

        Args:
          val:    Either FARENHEIT or CELSIUS
        """
        meta = {'units': val}
        if val in [Thermostat.FARENHEIT, Thermostat.CELSIUS]:
            self.db.set_meta('thermostat', meta)
        else:
            LOG.error("Bad value %s, for units on Thermostat %s.", val,
                      self.addr)

    #-----------------------------------------------------------------------
    def pair(self, on_done=None):
        """Wrapper for Base.Pair().

        This wraps the Base.Pair() function so that we can call the enable
        broadcast flag when pairing is complete.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Thermostat %s pairing", self.addr)

        # Build a sequence of calls to the do the pairing.
        seq = CommandSeq(self, "Thermostat paired", on_done, name="DevPair")

        # Do normal pair first.
        seq.add(super().pair)

        # Ask the device to enable the broadcast messages, otherwise the
        # direct messages such as temp changes are not sent to the modem
        seq.add(self.enable_broadcast)

        # Run the sequence
        seq.run()

    #-----------------------------------------------------------------------
    def refresh(self, force=False, on_done=None):
        """Refresh the current device state and database if needed.

        This sends a ping to the device.  The reply has the current device
        state (on/off, level, etc) and the current db delta value which is
        checked against the current db value.  If the current db is out of
        date, it will trigger a download of the database.

        This will send out an updated signal for the current device status
        whenever possible.

        In addition, this also runs the 'get_status' command as well, which
        asks the thermostat for the current state of its attributes as well
        the current units selected on the device.  If you are seeing errors
        in temperatures that look like C and F are reversed, running a refresh
        may fix the issue.

        Args:
          force (bool):  If true, will force a refresh of the device database
                even if the delta value matches as well as a re-query of the
                device model information even if it is already known.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Device %s cmd: fan status refresh", self.addr)

        seq = CommandSeq(self, "Refresh complete", on_done, name="DevRefresh")

        # Send a 0x19 0x03 command to get the fan speed level.  This sends a
        # refresh ping which will respond w/ the fan level and current
        # database delta field.  Pass skip_db here - we'll let the dimmer
        # refresh handler above take care of getting the database updated.
        # Otherwise this handler and the one created in the dimmer refresh
        # would download the database twice.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x03)
        msg_handler = handler.DeviceRefresh(self, self.handle_refresh,
                                            force=False, num_retry=3,
                                            skip_db=True)
        seq.add_msg(msg, msg_handler)

        # If we get the FAN state correctly, then have the dimmer also get
        # it's state and update the database if necessary.
        seq.add(self.get_status)
        seq.run()

    #-----------------------------------------------------------------------
    def get_status(self, on_done=None):
        """Request the status of the common attributes of the thermostat

        Gets the mode state, current temp, heating/cooling state, fan mode,
        cool setpoint, heat setpoint, and ambient humidity.  Will then emit
        all necessary signal_* events to cause mqtt messages to be sent

        Also receives the units (C or F) selected on the thermostat which is
        important for understanding the ambient temp and set point.  If you see
        odd temperature values, try running 'get_status' or 'refresh'

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x02,
                                     bytes([0x00] * 14), crc_type="CRC")
        msg_handler = handler.ExtendedCmdResponse(msg, self.handle_status,
                                                  on_done, num_retry=3)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_status(self, msg, on_done=None):
        """Handle the response to the get_status message.

        Gets the mode state, current temp, heating/cooling state, fan mode,
        cool setpoint, heat setpoint, and ambient humidity.  Will then emit
        all necessary signal_* events to cause mqtt messages to be sent

        Args:
          msg:   (InpStandard) Broadcast message from the device.
        """
        on_done = util.make_callback(on_done)

        # The response contains the following data payload
        # D11 - Status Flag.  Processed first, because we need to know Units
        # to calculate some of this.
        status_flag = int.from_bytes(msg.data[10:11], byteorder='big')
        self.process_status_flag(status_flag)

        # D2 - Day
        # D3 - Hour
        # D4 - Minute
        # D5 - Second

        # D6 - Sys Mode*16 + Fanmode
        sys_byte = int.from_bytes(msg.data[5:6], byteorder='big')
        # Fan first bit only
        fan_nibble = sys_byte & 0b1
        self.set_fan_mode_state(fan_nibble)
        # Mode
        mode_nibble = sys_byte >> 4
        try:
            hvac_mode = Thermostat.Mode(mode_nibble)
        except ValueError:
            LOG.exception("Unknown mode status state %s.", mode_nibble)
        else:
            self.signal_mode_change.emit(self, hvac_mode)

        # D7 - Cool Set Point in the Units specified on the device
        cool_sp = int.from_bytes(msg.data[6:7], byteorder='big')
        if self.units == Thermostat.FARENHEIT:
            cool_sp = (cool_sp - 32) * 5 / 9
        self.signal_cool_sp_change.emit(self, cool_sp)

        # D8 - Humidity
        humid = int.from_bytes(msg.data[7:8], byteorder='big')
        self.signal_ambient_humid_change.emit(self, humid)

        # D9 - Temp high byte - Celsius *10
        # D10 - Temp low byte - Celsius *10
        temp_c = int.from_bytes(msg.data[8:10], byteorder='big') / 10
        self.signal_ambient_temp_change.emit(self, temp_c)

        # D12 - Heat Set Point in the Units specified on the device
        heat_sp = int.from_bytes(msg.data[11:12], byteorder='big')
        if self.units == Thermostat.FARENHEIT:
            heat_sp = (heat_sp - 32) * 5 / 9
        self.signal_heat_sp_change.emit(self, heat_sp)

        on_done(True, "Status recevied", None)

    #-----------------------------------------------------------------------
    def process_status_flag(self, flag):
        """Process the status flag from the get_status message.

        Deciphers the status flag and then emits all the signals for the
        relevant changes.  Sadly, the layout of the status flag is not
        consistent across the thermostat spec, so this cannot be reused by
        other functions

        Args:
          flag (int):   The status flag bits.
        """
        # I have not figured out what the last three bits are.  Program lock
        # is likely one of them.  As is 12/24 hour, perhaps button beep,
        # button lock, or backlight?  This also seems like a messy way to
        # handle this, is there a better way?
        cooling = flag & 1
        heating = flag >> 1 & 1
        energy = flag >> 2 & 1
        self.units = flag >> 3 & 1
        hold = flag >> 4 & 1

        # Signal status change
        status = Thermostat.Status.OFF
        if cooling:
            status = Thermostat.Status.COOLING
        elif heating:
            status = Thermostat.Status.HEATING
        self.signal_status_change.emit(self, status)

        # Signal hold state and energy.
        self.signal_hold_change.emit(self, bool(hold))
        self.signal_energy_change.emit(self, bool(energy))

    #-----------------------------------------------------------------------
    def set_fan_mode_state(self, mode):
        """Signals a change in the fan mode

        The mode is deciphered using the Thermostat.Mode enum class

        Args:
          mode (int):  An int which matches the options in Thermostat.Fanmode
        """
        try:
            fan_mode = Thermostat.Fan(mode)
        except ValueError:
            LOG.exception("Unknown fan mode state %s.", mode)
        else:
            self.signal_fan_mode_change.emit(self, fan_mode)

    #-----------------------------------------------------------------------
    def get_humidity_setpoints(self, on_done=None):
        """Requests an extended message which has details about the
        humidity setpoints.  No other known way to obtain them.

        Not currently enabled, the handle_humidity_status function
        needs to be fleshed out for this to work.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        msg = Msg.OutExtended.direct(
            self.addr, 0x2e, 0x00, bytes([0x00] * 2 + [0x01] + [0x00] * 11),
            crc_type="CRC")
        msg_handler = handler.ExtendedCmdResponse(
            msg, self.handle_humidity_setpoints, on_done, num_retry=3)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_humidity_setpoints(self, msg, on_done=None):
        """Handle the humidity status request, contains a lot of duplicate
        data which is already present in a get_status() request.

        Not currently enabled

        Args:
          msg (InpStandard): Broadcast message from the device.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # The response looks like
        # D4 - High Humid Set Point
        # D5 - Low Humid Set Point
        # D6 - Firmware
        # D7 - Cool Set Point
        # D8 - Heat Set Point
        # D9 - RF Offset
        # D10 - Energy Saving Setback
        # D11 - External Temp Offset
        # D12 - Is Status Report Enabled
        #
        # Not coded up yet
        pass

    #-----------------------------------------------------------------------
    def enable_broadcast(self, on_done=None):
        """Request the thermostat to broadcast changes in setpoints, temp,
        mode, and humidity

        Requires a 0xEF group responder entry to be in the device's link
        database to have any effect.  This is called automatically anytime
        pair() is run.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00,
                                     bytes([0x00] + [0x08] + [0x00] * 12))
        msg_handler = handler.StandardCmd(msg, self.handle_generic_ack,
                                          on_done, num_retry=3)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_generic_ack(self, msg, on_done=None):
        """Handles generic ack responses where there is nothing to do.

        Generally the reason there is nothing to do is that the thermostat
        will send a subsequent direct message through which we can update
        the necessary state

        Args:
          msg (InpStandard): Direct ACK message from the device.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        on_done = util.make_callback(on_done)

        LOG.debug("Thermostat %s generic ack recevied", self.addr)
        on_done(True, "Thermostat generic ack recevied", None)

    #-----------------------------------------------------------------------
    def handle_message(self, msg):
        """Handle broadcast messages from this device.

        Group broadcast messages are sent for Cooling, Heating, humidifying
        and de-humidifying.  This handles those messages and emits the
        appropriate signal to cause the mqtt message to be sentself.

        Currently we don't do anything with the humidifying messages.

        Args:
          msg (InpStandard): Broadcast message from the device.
        """
        if msg.cmd1 == Msg.CmdType.LINK_CLEANUP_REPORT:
            LOG.info("Thermostat %s broadcast ACK grp: %s", self.addr,
                     msg.group)
            return
        elif msg.cmd1 in [Msg.CmdType.ON, Msg.CmdType.OFF]:
            LOG.info("Thermostat %s broadcast %s grp: %s", self.addr, msg.cmd1,
                     msg.group)

            try:
                condition = Thermostat.Groups(msg.group)
            except ValueError:
                LOG.exception("Unknown thermostat group %s.", msg.group)
                return

            LOG.info("Thermostat %s signaling condition %s", self.addr,
                     condition)

            # Only handling Heating and Cooling, not humidifying yet
            if condition in [Thermostat.Groups.HEATING,
                             Thermostat.Groups.COOLING]:
                if msg.cmd1 == 0x13:
                    status = Thermostat.Status.OFF
                elif condition is Thermostat.Groups.HEATING:
                    status = Thermostat.Status.HEATING
                else:
                    status = Thermostat.Status.COOLING

                self.signal_status_change.emit(self, status)

        # As long as there is no errors (which return above), call
        # handle_broadcast for any device that we're the controller of.
        self.update_linked_devices(msg)

    #-----------------------------------------------------------------------
    def mode_command(self, mode):
        """Command the Thermostat to change modes.

        Validity of the command is handled by the MQTT topic handler.

        Args:
          mode (Thermostat.ModeCommands):  The mode to change.
        """
        # Send the command to the thermostat
        msg = Msg.OutExtended.direct(self.addr, 0x6b, mode.value,
                                     bytes([0x00] * 14))
        msg_handler = handler.StandardCmd(msg, self.handle_mode_command,
                                          None, num_retry=3)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_mode_command(self, msg, on_done=None):
        """Receives the ack from the mode command message.

        Not truly necessary.  If the mode changes, the thermostat will send
        a direct 'broadcast' command with the new mode.  However, if the mode
        on the device isn't changing, no message is sent, which could be
        confusing in certain circumstances

        Args:
          msg (InpStandard): Direct ACK message from the device.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        on_done = util.make_callback(on_done)

        if msg.cmd1 == 0x6b:
            self.signal_mode_change.emit(self,
                                         Thermostat.ModeCommands(msg.cmd2))
            on_done(True, "Thermostat recevied mode command", None)

        else:
            LOG.debug("Thermostat %s received a bad ack %s", self.addr,
                      msg.cmd1)
            on_done(False, "Wrong direct ack received", None)

    #-----------------------------------------------------------------------
    def fan_command(self, fan):
        """Command the Thermostat to change fan modes.

        Validity of the command is handled by the MQTT topic handler.

        Args:
          fan (Thermostat.FanCommands): The fan command to send.
        """
        # Send the command to the thermostat
        msg = Msg.OutExtended.direct(self.addr, 0x6b, fan.value,
                                     bytes([0x00] * 14))
        msg_handler = handler.StandardCmd(msg, self.handle_fan_command,
                                          None, num_retry=3)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_fan_command(self, msg, on_done=None):
        """Receives the ack from the fan mode command message.

        Not truly necessary.  If the fan mode changes, the thermostat will send
        a direct 'broadcast' command with the new fan mode.  However, if the
        fan mode on the device isn't changing, no message is sent, which could
        be confusing in certain circumstances

        Args:
          msg (InpStandard): Direct ACK message from the device.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        on_done = util.make_callback(on_done)

        if msg.cmd1 == 0x6b:
            self.signal_fan_mode_change.emit(self,
                                             Thermostat.FanCommands(msg.cmd2))
            on_done(True, "Thermostat recevied fan mode command", None)

        else:
            LOG.debug("Thermostat %s received a bad ack %s", self.addr,
                      msg.cmd1)
            on_done(False, "Wrong direct ack received", None)

    #-----------------------------------------------------------------------
    def heat_sp_command(self, temp_c):
        """Command the Thermostat to change the heat setpoint.

        Validity of the command is handled by the MQTT topic handler.

        Args:
          temp_c:   temperature in celsius
        """
        # Convert to proper units
        temp = temp_c
        if self.units == Thermostat.FARENHEIT:
            temp = (temp_c * 9.0 / 5.0) + 32

        # Limit temp range
        temp = 0 if temp < 0 else temp
        temp = 127 if temp > 127 else temp

        # Send the command to the thermostat in units on thermo * 2
        msg = Msg.OutExtended.direct(self.addr, 0x6d, int(temp * 2),
                                     bytes([0x00] * 14))
        msg_handler = handler.StandardCmd(msg, self.handle_heat_sp_command,
                                          None, num_retry=3)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_heat_sp_command(self, msg, on_done=None):
        """Receives the ack from the heat setpoint command message.

        Not truly necessary.  If the setpoint changes, the thermostat will
        send a direct 'broadcast' command with the new setpoint.  However,
        if the setpoint on the device isn't changing, no message is sent, which
        could be confusing in certain circumstances

        Args:
          msg (InpStandard) Direct ACK message from the device.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        on_done = util.make_callback(on_done)

        if msg.cmd1 == 0x6d:
            heat_sp = msg.cmd2 / 2
            if self.units == Thermostat.FARENHEIT:
                heat_sp = (heat_sp - 32) * 5 / 9

            self.signal_heat_sp_change.emit(self, heat_sp)
            on_done(True, "Thermostat recevied heat setpoint command", None)

        else:
            LOG.debug("Thermostat %s received a bad ack %s", self.addr,
                      msg.cmd1)
            on_done(False, "Wrong direct ack received", None)

    #-----------------------------------------------------------------------
    def cool_sp_command(self, temp_c):
        """Command the Thermostat to change the cool setpoint.

        Validity of the command is handled by the MQTT topic handler.

        Args:
          temp_c:   temperature in celsius
        """
        # Convert to proper units
        temp = temp_c
        if self.units == Thermostat.FARENHEIT:
            temp = (temp_c * 9 / 5) + 32

        # Limit temp range
        temp = 0 if temp < 0 else temp
        temp = 127 if temp > 127 else temp

        # Send the command to the thermostat in units on thermo * 2
        msg = Msg.OutExtended.direct(self.addr, 0x6c, int(temp * 2),
                                     bytes([0x00] * 14))
        msg_handler = handler.StandardCmd(msg, self.handle_cool_sp_command,
                                          None, num_retry=3)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_cool_sp_command(self, msg, on_done=None):
        """Receives the ack from the cool setpoint command message.

        Not truly necessary.  If the setpoint changes, the thermostat will
        send a direct 'broadcast' command with the new setpoint.  However,
        if the setpoint on the device isn't changing, no message is sent, which
        could be confusing in certain circumstances

        Args:
          msg:   (InpStandard) Direct ACK message from the device.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        on_done = util.make_callback(on_done)

        if msg.cmd1 == 0x6c:
            cool_sp = msg.cmd2 / 2
            if self.units == Thermostat.FARENHEIT:
                cool_sp = (cool_sp - 32) * 5 / 9

            self.signal_cool_sp_change.emit(self, cool_sp)
            on_done(True, "Thermostat recevied cool setpoint command", None)

        else:
            LOG.debug("Thermostat %s received a bad ack %s", self.addr,
                      msg.cmd1)
            on_done(False, "Wrong direct ack received", None)
