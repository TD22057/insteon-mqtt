#===========================================================================
#
# Input insteon user factory reset message.
#
#===========================================================================
from .Base import Base


class InpUserReset(Base):
    """User reset the PLM modem.

    This is sent from the PLM modem to the host when the user does a factory
    reset on the modem.
    """
    # pylint: disable=abstract-method

    msg_code = 0x55
    fixed_msg_size = 2

    #-----------------------------------------------------------------------
    @classmethod
    def from_bytes(cls, raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw) >=
        msg_size().

        Args:
          raw (bytes):  The current byte stream to read from.

        Returns:
          Returns the constructed message object.
        """
        assert len(raw) >= InpUserReset.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == InpUserReset.msg_code

        return InpUserReset()

    #-----------------------------------------------------------------------
    def __init__(self):
        """Constructor
        """
        # pylint: disable=useless-super-delegation
        super().__init__()

    #-----------------------------------------------------------------------
    def __str__(self):
        return "User reset"

    #-----------------------------------------------------------------------

#===========================================================================
