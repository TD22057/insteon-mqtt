#===========================================================================
#
# Host->PLM standard direct message
#
#===========================================================================
import io
from ..Address import Address
from .Flags import Flags

#===========================================================================

class OutAllLinkGetNext:
    """Direct, standard message from host->PLM.

    When sending, this will be 8 bytes long.  When receiving back from
    the modem, it will be 9 bytes (8+ack/nak).  
    """
    code = 0x6a
    msg_size = 3

    #-----------------------------------------------------------------------
    @staticmethod
    def read(raw):
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
        assert(raw[0] == 0x02 and raw[1] == OutAllLinkGetNext.code)

        # Make sure we have enough bytes to read the message.
        if OutAllLinkGetNext.msg_size > len(raw):
            return OutAllLinkGetNext.msg_size

        is_ack = raw[2] == 0x06
        return OutAllLinkGetNext(is_ack)
        
    #-----------------------------------------------------------------------
    def __init__(self, is_ack=None):
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def raw(self):
        return bytes([0x02, self.code])

    #-----------------------------------------------------------------------
    def __str__(self):
        return "All link get next: ack: %s" % self.is_ack

    #-----------------------------------------------------------------------
    
#===========================================================================
