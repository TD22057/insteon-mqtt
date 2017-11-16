#===========================================================================
#
# Input insteon standard and extended message.
#
#===========================================================================
import io
from ..Address import Address
from .Flags import Flags


class InpStandard:
    """Direct, standard message.

    This is sent from the PLM modem to the host when various
    conditions happen.  Standard messages are general purpose - they
    can contain a lot of different data and it's up to the message
    handler to interpret the results.
    """
    msg_code = 0x50
    fixed_msg_size = 11

    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw)
        >= msg_size().

        Args:
           raw   (bytes): The current byte stream to read from.

        Returns:
           Returns the constructed message object.
        """
        assert len(raw) >= InpStandard.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == InpStandard.msg_code

        # Read the message flags first to see if we have an extended
        # message.  If we do, make sure we have enough bytes.
        from_addr = Address.from_bytes(raw, 2)
        to_addr = Address.from_bytes(raw, 5)
        flags = Flags.from_bytes(raw, 8)
        cmd1 = raw[9]
        cmd2 = raw[10]
        return InpStandard(from_addr, to_addr, flags, cmd1, cmd2)

    #-----------------------------------------------------------------------
    def __init__(self, from_addr, to_addr, flags, cmd1, cmd2):
        """Constructor

        Args:
          from_addr:  (Address) The from device address.
          to_addr:    (Address) The to device address.
          flags:      (Flags) The message flags.
          cmd1:       (int) The command 1 byte.
          cmd2:       (int) The command 2 byte.
        """
        assert isinstance(flags, Flags)

        self.from_addr = from_addr
        self.to_addr = to_addr
        self.flags = flags
        self.cmd1 = cmd1
        self.cmd2 = cmd2
        self.group = None
        if self.flags.is_broadcast:
            self.group = self.to_addr.ids[2]
        elif (self.flags.type == Flags.ALL_LINK_CLEANUP or
              self.flags.type == Flags.CLEANUP_ACK):
            self.group = self.cmd2

    #-----------------------------------------------------------------------
    def __str__(self):
        if self.group is None:
            return "Std: %s->%s %s cmd: %02x %02x" % \
                (self.from_addr, self.to_addr, self.flags, self.cmd1, self.cmd2)
        else:
            return "Std: %s %s grp: %02x cmd: %02x %02x" % \
                (self.from_addr, self.flags, self.group, self.cmd1, self.cmd2)


    #-----------------------------------------------------------------------

#===========================================================================
class InpExtended:
    """Direct, extended message from PLM->host.

    The extended message is used by specialized devices to report
    state as well as when a device reports it's all link database
    records.
    """
    msg_code = 0x51
    fixed_msg_size = 25

    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw)
        >= msg_size().

        Args:
           raw   (bytes): The current byte stream to read from.

        Returns:
           Returns the constructed OutStandard or OutExtended object.
        """
        assert len(raw) >= InpExtended.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == InpExtended.msg_code

        from_addr = Address.from_bytes(raw, 2)
        to_addr = Address.from_bytes(raw, 5)
        flags = Flags.from_bytes(raw, 8)
        cmd1 = raw[9]
        cmd2 = raw[10]
        data = raw[11:25]
        return InpExtended(from_addr, to_addr, flags, cmd1, cmd2, data)

    #-----------------------------------------------------------------------
    def __init__(self, from_addr, to_addr, flags, cmd1, cmd2, data):
        """Constructor

        Args:
          from_addr:  (Address) The from device address.
          to_addr:    (Address) The to device address.
          flags:      (Flags) The message flags.
          cmd1:       (int) The command 1 byte.
          cmd2:       (int) The command 2 byte.
          data:       (bytes) 14 byte extended data array.
        """
        assert len(data) == 14

        self.from_addr = from_addr
        self.to_addr = to_addr
        self.flags = flags
        self.cmd1 = cmd1
        self.cmd2 = cmd2
        self.data = data
        self.group = None
        if self.flags.is_broadcast:
            self.group = self.to_addr.ids[2]
        elif (self.flags.type == Flags.ALL_LINK_CLEANUP or
              self.flags.type == Flags.CLEANUP_ACK):
            self.group = self.cmd2

    #-----------------------------------------------------------------------
    def __str__(self):
        o = io.StringIO()
        if self.group is None:
            o.write("Ext: %s->%s %s cmd: %02x %02x\n" %
                    (self.from_addr, self.to_addr, self.flags, self.cmd1,
                     self.cmd2))
        else:
            o.write("Ext: %s %s grp: %02x cmd: %02x %02x" % \
                    (self.from_addr, self.flags, self.group, self.cmd1,
                     self.cmd2))

        for i in self.data:
            o.write("%02x " % i)
        return o.getvalue()

    #-----------------------------------------------------------------------

#===========================================================================
