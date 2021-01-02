#===========================================================================
#
# Unreachable Message from the Modem
#
#===========================================================================
from ..Address import Address
from .Base import Base
from .Flags import Flags


class Unreachable(Base):
    """This message has only been seen on the Hub and is not documented.

    The messages in the 0x50+ range are commands sent from the modem.
    This 0x5c message is not documented anywhere, it was first seen on the Hub2
    but could be incorporated into PLM models as well.

    The message is not critical, it tells us information we could already
    derive when we don't see a message response from the device.  It certainly
    provides more certainty, and may arrive faster than what we would
    otherwise determine on our own.

    Currently, the message is just logged and then ignored.
    """
    # pylint: disable=abstract-method

    msg_code = 0x5c
    # The messages we see are almost certainly an ack as the last byte is
    # always 0x06.
    fixed_msg_size = 11

    #-----------------------------------------------------------------------
    @classmethod
    def from_bytes(cls, raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw) >=
        msg_size().

        Args:
          raw (bytes):  The current byte stream to read from.

        Returns:
          Returns the constructed InpUserSetBtn object.
        """
        assert len(raw) >= Unreachable.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == Unreachable.msg_code

        # Read the message flags first to see if we have an extended message.
        # If we do, make sure we have enough bytes.
        from_addr = Address.from_bytes(raw, 2)
        to_addr = Address.from_bytes(raw, 5)
        flags = Flags.from_bytes(raw, 8)
        cmd1 = raw[9]
        cmd2 = raw[10]
        return Unreachable(from_addr, to_addr, flags, cmd1, cmd2)

    #-----------------------------------------------------------------------
    def __init__(self, from_addr, to_addr, flags, cmd1, cmd2):
        """Constructor

        Args:
          from_addr (Address):  The from device address.
          to_addr (Address):  The to device address.
          flags (Flags):  The message flags.
          cmd1 (int):  The command 1 byte.
          cmd2 (int):  The command 2 byte.
        """
        super().__init__()

        assert isinstance(flags, Flags)

        self.from_addr = from_addr
        self.to_addr = to_addr
        self.flags = flags
        self.cmd1 = cmd1
        self.cmd2 = cmd2

    #-----------------------------------------------------------------------
    def __str__(self):
        return ("Unreachable: %s->%s %s cmd: %02x %02x" %
                (self.from_addr, self.to_addr, self.flags, self.cmd1,
                 self.cmd2))

    #-----------------------------------------------------------------------

#===========================================================================
