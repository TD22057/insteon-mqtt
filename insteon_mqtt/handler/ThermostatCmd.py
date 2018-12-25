#===========================================================================
#
# Thermostat direct message handler.
#
#===========================================================================
import enum
from .. import log
from .. import message as Msg
from .Base import Base

LOG = log.get_logger()


class ThermostatCmd(Base):
    """Thermostat direct message handler.

    The thermostats send direct messages concerning changes in their
    temp, humid, mode, and status.  This catches those messages,
    confirms they are sent from a thermostat and processes them
    accordingly.

    This hander is added to the protocol handlers whenever a thermostat is 
    loaded.

    NOTE: This handler is designed to always be active - it never returns
    FINISHED.
    """
    # Irritatingly, this mapping is different for direct status messages.
    # Insteon loves to be irritating like that
    class Mode(enum.IntEnum):
        OFF = 0x00
        HEAT = 0x01
        COOL = 0x02
        AUTO = 0x03
        PROGRAM = 0x04

    def __init__(self, device):
        """Constructor

        Args
          device:   (Device) The Insteon thermostat object.
        """
        super().__init__()
        self.device = device

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        Try and process the message.

        Args:
          protocol:  (Protocol) The Insteon Protocol object
          msg:       Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        STATUS_TEMP     = 0x6e
        STATUS_HUMID    = 0x6f
        STATUS_MODE     = 0x70
        STATUS_COOL_SP  = 0x71
        STATUS_HEAT_SP  = 0x72

        # Confirm this is a message we can handle
        if not isinstance(msg, Msg.InpStandard):
            return Msg.UNKNOWN

        # Make sure this is the right device and message type
        device = self.device.modem.find(msg.from_addr)
        if not device:
            LOG.debug("Unknown direct device %s", msg.from_addr)
            return Msg.UNKNOWN
        elif device != self.device:
            LOG.debug("This handler doesn't handle this device %s",
                      msg.from_addr)
            return Msg.UNKNOWN
        elif msg.flags.type != Msg.Flags.Type.DIRECT:
            LOG.debug("This handler doesn't handle this type of message %s",
                      Msg.Flags.Type)
            return Msg.UNKNOWN

        # Pull out and process the commands that this handler handles
        if msg.cmd1 == STATUS_TEMP:
            temp = int(msg.cmd2)
            if self.device.units == self.device.FARENHEIT:
                temp = (temp - 32) * 5/9
            self.device.signal_ambient_temp_change.emit(self.device, temp)
            return Msg.CONTINUE
        elif msg.cmd1 == STATUS_HUMID:
            self.device.signal_humid_change.emit(self.device, int(msg.cmd2))
            return Msg.CONTINUE
        elif msg.cmd1 == STATUS_MODE:
            fan_nibble = int(msg.cmd2) >> 4
            mode_nibble = int(msg.cmd2) & 0b00001111
            self.device.set_fan_mode_state(fan_nibble)
            try:
                hvac_mode = ThermostatCmd.Mode(mode_nibble)
            except ValueError:
                LOG.exception("Unknown mode broadcast state %s.", mode_nibble)
            else:
                self.device.signal_mode_change.emit(self.device, hvac_mode)
            return Msg.CONTINUE
        elif msg.cmd1 == STATUS_COOL_SP:
            cool_sp = int(msg.cmd2)
            if self.device.units == self.device.FARENHEIT:
                cool_sp = (cool_sp - 32) * 5/9
            self.device.signal_cool_sp_change.emit(self.device, cool_sp)
            return Msg.CONTINUE
        elif msg.cmd1 == STATUS_HEAT_SP:
            heat_sp = int(msg.cmd2)
            if self.device.units == self.device.FARENHEIT:
                heat_sp = (heat_sp - 32) * 5/9
            self.device.signal_heat_sp_change.emit(self.device, heat_sp)
            return Msg.CONTINUE
        else:
            return Msg.UNKNOWN

        # Different message flags than we exepcted.
        return Msg.UNKNOWN
