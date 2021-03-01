#===========================================================================
#
# Output insteon reset the PLM modem message.
#
#===========================================================================
from .Base import Base


class OutGetModemFlags(Base):
    """Command requesting the modem configuration

    This command will retun 6 bytes:
      - 0x02
      - 0x73
      - Modem Configuration Flags
      - Spare 1
      - Spare 2
      - Ack/Nak
    """
    msg_code = 0x73
    fixed_msg_size = 6

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
        modem_flags = raw[2]
        spare1 = raw[3]
        spare2 = raw[4]
        is_ack = raw[5] == 0x06
        return OutGetModemFlags(is_ack, modem_flags, spare1, spare2)

    #-----------------------------------------------------------------------
    def __init__(self, is_ack=None, modem_flags=None, spare1=None,
                 spare2=None):
        """Constructor

        Args:
          is_ack (bool):  True for ACK, False for NAK.  None for output
                 commands to the modem.
        """
        super().__init__()

        self.is_ack = is_ack
        self.modem_flags = modem_flags
        self.spare1 = spare1
        self.spare2 = spare2

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the message to a byte array.

        Returns:
          bytes:  Returns the message as bytes.
        """
        return bytes([0x02, self.msg_code])

    #-----------------------------------------------------------------------
    def __str__(self):
        ack = ""
        flags = ""
        spares = ""
        if self.is_ack is not None:
            ack = " ack: %s" % str(self.is_ack)
            flags = " modem flags: %s" % str(self.modem_flags)
            spares = " spares: %s %s" % (str(self.spare1), str(self.spare2))
        return "OutGetModemFlags%s%s%s" % (flags, spares, ack)

    #-----------------------------------------------------------------------

#===========================================================================
