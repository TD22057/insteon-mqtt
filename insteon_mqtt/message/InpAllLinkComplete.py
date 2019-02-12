#===========================================================================
#
# Input insteon all link complete message.
#
#===========================================================================
import enum
from .Base import Base
from ..Address import Address


class InpAllLinkComplete(Base):
    """All linking complete.

    This is sent from the PLM modem to the host when linking between the PLM
    modem and a device is completed.
    """
    # pylint: disable=abstract-method

    msg_code = 0x53
    fixed_msg_size = 10

    # Link command codes
    class Cmd(enum.IntEnum):
        RESPONDER = 0x00
        CONTROLLER = 0x01
        DELETE = 0xff

    #-----------------------------------------------------------------------
    @classmethod
    def from_bytes(cls, raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw) >=
        msg_size().

        Args:
          raw bytes:  The current byte stream to read from.

        Returns:
          Returns the constructed OutStandard or OutExtended object.
        """
        assert len(raw) >= cls.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == cls.msg_code

        cmd = cls.Cmd(raw[2])
        group = raw[3]
        addr = Address.from_bytes(raw, 4)
        dev_cat = raw[7]
        dev_subcat = raw[8]
        firmware = raw[9]
        return InpAllLinkComplete(cmd, group, addr, dev_cat, dev_subcat,
                                  firmware)

    #-----------------------------------------------------------------------
    def __init__(self, cmd, group, addr, dev_cat, dev_subcat, firmware):
        """Constructor

        Args:
          cmd (Cmd):  Command byte.  See the InpAllLinkComplete.Cmd
              enumeration for valid values.
          group (int):  The all link group of the link.
          addr (Address):  The address of the device being linked.
          dev_cat (int):  The device category.
          dev_subcat (int):  The device subcategory.
          firmware (int):  The firmware revision.
        """
        super().__init__()

        self.cmd = self.Cmd(cmd)
        self.group = group
        self.addr = addr
        self.dev_cat = dev_cat
        self.dev_subcat = dev_subcat
        self.firmware = firmware

    #-----------------------------------------------------------------------
    def __str__(self):
        return ("All link done: %s grp: %d %s cat: %#04x %#04x %#04x" %
                (self.addr, self.group, self.cmd, self.dev_cat,
                 self.dev_subcat, self.firmware))

    #-----------------------------------------------------------------------

#===========================================================================
