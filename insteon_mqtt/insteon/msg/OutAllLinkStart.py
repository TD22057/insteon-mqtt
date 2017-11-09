#===========================================================================
#
# Host->PLM standard direct message
#
#===========================================================================
import io
from ..Address import Address
from .Flags import Flags

#===========================================================================

class OutAllLinkStart:
    """Direct, standard message from host->PLM.

    When sending, this will be 8 bytes long.  When receiving back from
    the modem, it will be 9 bytes (8+ack/nak).  
    """
    code = 0x64
    msg_size = 5

    RESPONDER = 0x01
    CONTROLLER = 0x03
    DELETE = 0xff

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
        assert(raw[0] == 0x02 and raw[1] == OutAllLinkStart.code)

        # Make sure we have enough bytes to read the message.
        if OutAllLinkStart.msg_size > len(raw):
            return OutAllLinkStart.msg_size

        link = raw[2]
        group = raw[3]
        is_ack = raw[4] == 0x06
        return OutAllLinkStart(link, group, is_ack)
        
    #-----------------------------------------------------------------------
    def __init__(self, link, group, is_ack=None):
        assert(link == self.RESPONDER or link == self.CONTROLLER or
               link == self.DELETE)
        
        self.link = link
        self.plm_responder = link == RESPONDER
        self.plm_controller = link == CONTROLLER
        self.is_delete = link == DELETE
        self.group = group
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def raw(self):
        return bytes([0x02, self.code, self.link, self.group])

    #-----------------------------------------------------------------------
    def __str__(self):
        lbl = { self.RESPONDER : 'rspd',
                self.CONTROLLER : 'ctrl',
                self.DELETE : 'del',
                }

        return "All link start: grp: %s %s ack: %s" % \
            (self.group, lbl[self.link], self.is_ack)

    #-----------------------------------------------------------------------
    
#===========================================================================
