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
from ..Signal import Signal

LOG = log.get_logger()


class Thermostat(Base):
    """Insteon Thermostat

    This works with the 2441TH line of Insteon Thermostats.  It will not work
    with the older Venstar Thermostats.

    The Thermostat 'broadcasts' alerts for a series of conditions using
    different broadcast group and direct messages.  This requires pairing
    the modem as a responder for all of the groups that the Thermostat
    uses.  The pair() method will do this automatically after
    the Thermostat is set as a responder to the modem (set modem, then
    Thermostat).

    When the thermostat alert is triggered, it will emit a signal
    using Thermostat.signal_*.

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

    # Irritatingly, this mapping is different for broadcast messages.
    # Insteon loves to be irritating like that.
    class Mode(enum.IntEnum):
        OFF = 0x00
        AUTO = 0x01
        HEAT = 0x02
        COOL = 0x03
        PROGRAM = 0x04

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
          name         (str) Nice alias name to use for the device.
        """
        # Set default values to attributes, may be overwritten by saved
        # values
        self.units = Thermostat.FARENHEIT

        super().__init__(protocol, modem, address, name)

        self.cmd_map.update({
            'get_status' : self.get_status
            })

        self.signal_ambient_temp_change = Signal()  # emit(device, Int temp_c)
        self.signal_fan_mode_change = Signal()  # emit(device, Fan fan mode)
        self.signal_mode_change = Signal()  # emit(device, Mode mode)
        self.signal_cool_sp_change = Signal()  # emit(device, Int cool_sp in c)
        self.signal_heat_sp_change = Signal()  # emit(device, Int heat_sp in c)
        self.signal_ambient_humid_change = Signal()  # emit(device, Int humid)
        self.signal_status_change = Signal() #emit(device, Str status)

        # Add handler for processing direct Messages
        protocol.add_handler(handler.ThermostatCmd(self))

    #-----------------------------------------------------------------------
    def pair(self, on_done=None):
        """Pair the device with the modem.

        This only needs to be called one time.  It will set the device
        as a controller and the modem as a responder for all of the
        groups that the device can alert on.

        This will also run the enable_broadcast command to ensure that
        the direct 'broadcast' messages are sent by the device.

        The device must already be a responder to the modem (such as by
        running the linking command) so we can update it's database.
        """
        LOG.info("Thermostat %s pairing", self.addr)

        # Build a sequence of calls to the do the pairing.  This insures each
        # call finishes and works before calling the next one.  We have to do
        # this for device db manipulation because we need to know the memory
        # layout on the device before making changes.
        seq = CommandSeq(self.protocol, "Thermostat paired", on_done)

        # Start with a refresh command - since we're changing the db, it must
        # be up to date or bad things will happen.
        seq.add(self.refresh)

        # Add the device as a responder to the modem on group 1.  This is
        # probably already there - and maybe needs to be there before we can
        # even issue any commands but this check insures that the link is
        # present on the device and the modem.
        seq.add(self.db_add_resp_of, 0x01, self.modem.addr, 0x01,
                refresh=False)

        # Now add the device as the controller of the modem for all the alert
        # types.
        for group_map in Thermostat.Groups:
            group = group_map.value
            seq.add(self.db_add_ctrl_of, group, self.modem.addr, group,
                    refresh=False)

        # Ask the device to enable the broadcast messages, otherwise the
        # direct messages such as temp changes are not sent to the modem
        seq.add(self.enable_broadcast)

        # Finally start the sequence running.  This will return so the
        # network event loop can process everything and the on_done callbacks
        # will chain everything together.
        seq.run()

    #-----------------------------------------------------------------------
    def get_status(self, on_done=None):
        """Request the status of the common attributes of the thermostat

        Gets the mode state, current temp, heating/cooling state, fan mode,
        cool setpoint, heat setpoint, and ambient humidity.  Will then emit
        all necessary signal_* events to cause mqtt messages to be sent

        Args:
          on_done:  Optional callback run when the commands are finished.
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
          msg:   (InptStandard) Broadcast message from the device.
        """
        # The response contains the following data payload

        # D11 - Status Flag
        # Processed first, because we need to know Units to calculate
        # some of this.
        # I have not figured out what all of these bits are
        # This also seems like a messy way to handle this, is there a better
        # way?  Would enum.flag be better? We don't every use this code
        # again.
        status_flag = int.from_bytes(msg.data[10:11], byteorder='big')
        print("Status Flag", msg.data[10:11], status_flag, format(status_flag, '0>8b'))
        Cooling = status_flag & 0b0000001
        Heating = status_flag & 0b0000010
        Energy =  status_flag & 0b0000100
        self.units =   status_flag & 0b0001000
        Hold =    status_flag & 0b0010000

        # Signal status change
        status = "OFF"
        if Cooling:
            status = "COOLING"
        elif Heating:
            status = "HEATING"
        self.signal_status_change.emit(self, status)

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
            HVAC_mode = Thermostat.Mode(mode_nibble)
        except ValueError:
            LOG.exception("Unknown mode status state %s.", mode_nibble)
        else:
            self.signal_mode_change.emit(self, HVAC_mode)

        # D7 - Cool Set Point in the Units specified on the device
        cool_sp = int.from_bytes(msg.data[6:7], byteorder='big')
        if self.units == Thermostat.FARENHEIT:
            cool_sp = (cool_sp - 32) * 5/9
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
            heat_sp = (heat_sp - 32) * 5/9
        self.signal_heat_sp_change.emit(self, heat_sp)

        on_done(True, "Status recevied", None)

    #-----------------------------------------------------------------------
    def set_fan_mode_state(self, mode):
        """Signals a change in the fan mode

        The mode is deciphered using the Thermostat.Mode enum class

        Args:
          mode:  An int which matches the options in Thermostat.Fanmode
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
          on_done:  Optional callback run when the commands are finished.
        """
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00,
                                     bytes([0x00] *2 + [0x01] + [0x00] * 11), crc_type="CRC")
        msg_handler = handler.ExtendedCmdResponse(msg, self.handle_humidity_status,
                                                  on_done, num_retry=3)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_humidity_status(self, msg, on_done=None):
        """Handle the humidity status request, contains a lot of duplicate
        data which is already present in a get_status() request.

        Not currently enabled

        Args:
          msg:   (InptStandard) Broadcast message from the device.
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
          on_done:  Optional callback run when the commands are finished.
        """
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00,
                                     bytes([0x00] + [0x08] + [0x00] * 12))
        msg_handler = handler.StandardCmd(msg, self.handle_enable_broadcast,
                                          on_done, num_retry=3)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_enable_broadcast(self, msg, on_done=None):
        """Handles the enable broadcast response.  Nothing to do.

        Args:
          on_done:  Optional callback run when the commands are finished.
        """
        LOG.info("Thermostat %s broadcast enabled", self.addr)
        on_done(True, "Thermostat broadcast enabled", None)


    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        """Handle broadcast messages from this device.

        Group broadcast messages are sent for Cooling, Heating, humidifying
        and de-humidifying.  This handles those messages and emits the
        appropriate signal to cause the mqtt message to be sentself.

        Currently we don't do anything with the humidifying messages.

        Args:
          msg:   (InptStandard) Broadcast message from the device.
        """
        # 0x11 is ON 0x13 is OFF.
        if msg.cmd1 in [0x11, 0x13]:
            LOG.info("Thermostat %s broadcast %s grp: %s", self.addr, msg.cmd1,
                     msg.group)

            try:
                condition = Thermostat.Groups(msg.group)
            except TypeError:
                LOG.exception("Unknown thermostat group %s.", msg.group)
                return

            LOG.info("Thermostat %s signaling condition %s", self.addr,
                     condition)

            # Only handling Heating and Cooling, not humidifying yet
            if condition in [Thermostat.Groups.HEATING,
                             Thermostat.Groups.COOLING]:
                if msg.cmd1 == 0x13:
                    self.signal_status_change.emit(self, "OFF")
                    return
                else:
                    self.signal_status_change.emit(self, condition.name)
                    return

        # As long as there is no errors (which return above), call
        # handle_broadcast for any device that we're the controller
        # of.
        super().handle_broadcast(msg)

    #-----------------------------------------------------------------------
