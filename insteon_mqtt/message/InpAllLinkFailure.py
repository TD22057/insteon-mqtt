#===========================================================================
#
# Input insteon all link failure message.
#
#===========================================================================
from ..Address import Address
from .Base import Base


class InpAllLinkFailure(Base):
    """User pressed the PLM set button.

    This is sent from the PLM modem to the host when all linking between the
    modem and a device fails.
    """
    # pylint: disable=abstract-method

    msg_code = 0x56
    fixed_msg_size = 7

    #-----------------------------------------------------------------------
    @classmethod
    def from_bytes(cls, raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw) >=
        msg_size().

        Args:
          raw (bytes):  The current byte stream to read from.

        Returns:
          Returns the constructed InpAllLinkFailure object.
        """
        assert len(raw) >= InpAllLinkFailure.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == InpAllLinkFailure.msg_code

        assert raw[2] == 0x01
        group = raw[3]
        addr = Address.from_bytes(raw, 4)
        return InpAllLinkFailure(group, addr)

    #-----------------------------------------------------------------------
    def __init__(self, group, addr):
        """Constructor

        Args:
          group (int):  The group the link is for.
          addr (Address):  The address of the device in the link.
        """
        super().__init__()

        self.group = group
        self.addr = addr

    #-----------------------------------------------------------------------
    def __str__(self):
        return "All link fail: %s grp: %d" % (self.addr, self.group)

    #-----------------------------------------------------------------------

#===========================================================================
