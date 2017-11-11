#===========================================================================
#
# Host->PLM standard direct message
#
#===========================================================================
import io
from ..Address import Address
from .Flags import Flags

#===========================================================================

class OutAllLink:
    """TODO: doc

    When sending, this will be 8 bytes long.  When receiving back from
    the modem, it will be 9 bytes (8+ack/nak).  
    """
    code = 0x61
    msg_size = 6

    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(raw):
        """Read the message from a byte stream.

        Args:
           raw   (bytes): The current byte stream to read from.  This
                 must be at least length 2.

        Returns:
           If an integer is returned, it is the number of bytes
           that need to be in the message to finish reading it.
           Otherwise the read message is returned.  This will return
           either an OutStandard or OutExtended message.
        """
        assert(len(raw) >= 2)
        assert(raw[0] == 0x02 and raw[1] == OutAllLink.code)

        # Make sure we have enough bytes to read the message.
        if OutAllLink.msg_size > len(raw):
            return OutAllLink.msg_size

        group = raw[2]
        cmd1 = raw[3]
        cmd2 = raw[4]
        is_ack = raw[5] == 0x06
        return OutAllLink(group, cmd1, cmd2, is_ack)
        
    #-----------------------------------------------------------------------
    def __init__(self, group, cmd1, cmd2, is_ack=None):
        self.group = group
        self.cmd1 = cmd1
        self.cmd2 = cmd2
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def to_bytes(self):
        return bytes([0x02, self.code,
                      self.group, self.cmd1, self.cmd2])

    #-----------------------------------------------------------------------
    def __str__(self):
        return "All link: grp: %s cmd: %#04x %#04x ack: %s" % \
            (self.group, self.cmd1, self.cmd2, self.is_ack)

    #-----------------------------------------------------------------------
    
#===========================================================================
