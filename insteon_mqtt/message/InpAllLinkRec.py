#===========================================================================
#
# PLM->host standard direct message
#
#===========================================================================
import io
from ..Address import Address
from .Flags import Flags
from .DbFlags import DbFlags

#===========================================================================

class InpAllLinkRec:
    """Direct, standard message from PLM->host.
    """
    code = 0x57
    msg_size = 10

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
        assert(raw[0] == 0x02 and raw[1] == InpAllLinkRec.code)

        # Make sure we have enough bytes to read the message.
        if InpAllLinkRec.msg_size > len(raw):
            return InpAllLinkRec.msg_size

        flags = DbFlags.from_bytes(raw, 2)
        group = raw[3]
        addr = Address.from_bytes(raw, 4)
        data = raw[7:10]
        
        return InpAllLinkRec(flags, group, addr, data)
        
    #-----------------------------------------------------------------------
    def __init__(self, flags, group, addr, data):
        assert(isinstance(flags, DbFlags))
        
        self.flags = flags
        self.group = group
        self.addr = addr
        self.data = data
        self.on_level = data[0]
        self.ramp_rate = data[1]

    #-----------------------------------------------------------------------
    def __str__(self):
        return "InpAllLinkRec: %s grp: %s %s data: %#04x %#04x %#04x" % \
            (self.addr, self.group, self.flags, self.data[0], self.data[1],
             self.data[2])

    #-----------------------------------------------------------------------
    def to_json(self):
        return {
            'type' : 'InpAllLinkRec',
            'addr' : self.addr.hex,
            'group' : self.group,
            'type' : 'CTRL' if self.flags.is_controller else 'RESP',
            'data' : self.data
            }
    
    #-----------------------------------------------------------------------
    
#===========================================================================
