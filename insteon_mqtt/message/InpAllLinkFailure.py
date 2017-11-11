#===========================================================================
#
# PLM->host standard direct message
#
#===========================================================================
import io
from ..Address import Address
from .Flags import Flags

#===========================================================================

class InpAllLinkFailure:
    """TODO
    """
    code = 0x56
    msg_size = 7

    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(raw):
        """Read the message from a byte stream.

        Args:
           raw   (bytes): The current byte stream to read from.  This
                 must be at least length 2.

        Returns:
           If an integer is returned, it is the number of bytes
           remaining to be read before calling from_bytes() again.
           Otherwise the read message is returned.  This will return
           either an OutStandard or OutExtended message.
        """
        assert(len(raw) >= 2)
        assert(raw[0] == 0x02 and raw[1] == InpAllLinkFailure.code)

        # Make sure we have enough bytes to read the message.
        if InpAllLinkFailure.msg_size > len(raw):
            return InpAllLinkFailure.msg_size

        assert(raw[2] == 0x01)
        group = raw[3]
        addr = Address.from_bytes(raw, 4)
        return InpAllLinkFailure(group, addr)
        
    #-----------------------------------------------------------------------
    def __init__(self, group, addr):
        self.group = group
        self.addr = addr

    #-----------------------------------------------------------------------
    def __str__(self):
        return "All link fail: %s grp: %d" % (self.addr, self.group)

    #-----------------------------------------------------------------------
    
#===========================================================================
