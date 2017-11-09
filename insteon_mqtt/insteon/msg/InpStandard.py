#===========================================================================
#
# PLM->host standard direct message
#
#===========================================================================
import io
from ..Address import Address
from .Flags import Flags

#===========================================================================

class InpStandard:
    """Direct, standard message from PLM->host.
    """
    code = 0x50
    msg_size = 11

    #-----------------------------------------------------------------------
    @staticmethod
    def read(raw):
        """Read the message from a byte stream.

        Args:
           raw   (bytes): The current byte stream to read from.  This
                 must be at least length 2.

        Returns:
           If an integer is returned, it is the number of bytes
           remaining to be read before calling read() again.
           Otherwise the read message is returned.  This will return
           either an OutStandard or OutExtended message.
        """
        assert(len(raw) >= 2)
        assert(raw[0] == 0x02 and raw[1] == InpStandard.code)

        # Make sure we have enough bytes to read the message.
        if InpStandard.msg_size > len(raw):
            return InpStandard.msg_size

        from_addr = Address.read(raw, 2)
        to_addr = Address.read(raw, 5)
        flags = Flags.read(raw, 8)
        cmd1 = raw[9]
        cmd2 = raw[10]
        return InpStandard(from_addr, to_addr, flags, cmd1, cmd2)
        
    #-----------------------------------------------------------------------
    def __init__(self, from_addr, to_addr, flags, cmd1, cmd2):
        assert(isinstance(flags, Flags))
        
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
