#===========================================================================
#
# Output insteon get first PLM database record message.
#
#===========================================================================
from .Base import Base


class OutAllLinkGetFirst(Base):
    """Get the first PLM modem all link database record.

    This is sent to the PLM modem to get start receiving the all link
    database.  The modem will respond with an echo/ACK of this message and an
    InpAllLinkRec message.  Once that message is received send an
    OutAllLinkGetNext to get receive the next message.
    """
    msg_code = 0x69
    fixed_msg_size = 3

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
          Returns the constructed message object.
        """
        assert len(raw) >= cls.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == cls.msg_code

        is_ack = raw[2] == 0x06
        return OutAllLinkGetFirst(is_ack)

    #-----------------------------------------------------------------------
    def __init__(self, is_ack=None):
        """Constructor

        Args:
          is_ack (bool):  True for ACK, False for NAK.  None for output
                 commands to the modem.
        """
        super().__init__()

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
        ack = "" if self.is_ack is None else " ack: %s" % self.is_ack
        return "All link get first%s" % ack

    #-----------------------------------------------------------------------

#===========================================================================
