#===========================================================================
#
# Output insteon get_info PLM modem message.
#
#===========================================================================
from .Base import Base
from ..Address import Address


class OutModemInfo(Base):
    """Command to reset the PLM modem.

    Send this command to get the address and model information from the modem.

    The modem will respond with an echo/ACK of this message with the requested
    information.
    """
    msg_code = 0x60
    fixed_msg_size = 9

    #-----------------------------------------------------------------------
    @classmethod
    def from_bytes(cls, raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw) >=
        msg_size().

        You cannot pass the output of to_bytes() to this.  to_bytes() is used
        to output to the PLM but the modem sends back the same message with
        an extra ack byte which this function can read.

        Args:
          raw (bytes):  The current byte stream to read from.

        Returns:
          Returns the constructed OutResetModem object.
        """
        assert len(raw) >= cls.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == cls.msg_code
        addr = Address.from_bytes(raw, 2)
        is_ack = raw[8] == 0x06

        return OutModemInfo(addr=addr,
                            dev_cat=raw[5],
                            sub_cat=raw[6],
                            firmware=raw[7],
                            is_ack=is_ack)

    #-----------------------------------------------------------------------
    def __init__(self, addr=None, dev_cat=None, sub_cat=None, firmware=None,
                 is_ack=None):
        """Constructor

        Args:
          is_ack (bool):  True for ACK, False for NAK.  None for output
                 commands to the modem.
        """
        super().__init__()

        self.addr = addr
        self.dev_cat = dev_cat
        self.sub_cat = sub_cat
        self.firmware = firmware
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the message to a byte array.

        Returns:
          bytes:  Returns the message as bytes.
        """
        return bytes([0x02, self.msg_code])

    #-----------------------------------------------------------------------
    def __str__(self):
        ack = "" if self.is_ack is None else " ack: %s" % str(self.is_ack)
        return "OutModemInfo%s" % ack

    #-----------------------------------------------------------------------

#===========================================================================
