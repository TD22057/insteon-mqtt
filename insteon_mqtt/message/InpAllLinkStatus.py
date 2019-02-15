#===========================================================================
#
# Input insteon all link status message.
#
#===========================================================================
from .Base import Base


class InpAllLinkStatus(Base):
    """All link cleanup status report.

    This is sent from the PLM modem to the host after a device has broadcast
    an all link broadcast message to activate a scene as an ACK/NAK of the
    broadcast.
    """
    # pylint: disable=abstract-method

    msg_code = 0x58
    fixed_msg_size = 3

    #-----------------------------------------------------------------------
    @classmethod
    def from_bytes(cls, raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw) >=
        msg_size().

        Args:
          raw (bytes):  The current byte stream to read from.

        Returns:
          Returns the constructed InpAllLinkStatus object.
        """
        assert len(raw) >= InpAllLinkStatus.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == InpAllLinkStatus.msg_code

        is_ack = raw[2] == 0x06
        return InpAllLinkStatus(is_ack)

    #-----------------------------------------------------------------------
    def __init__(self, is_ack):
        """Constructor

        Args:
          is_ack (bool):  True for ACK, False for NAK.
        """
        super().__init__()

        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def __str__(self):
        return "All link status ack: %d" % self.is_ack

    #-----------------------------------------------------------------------

#===========================================================================
