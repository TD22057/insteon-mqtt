#===========================================================================
#
# Host->PLM standard direct message
#
#===========================================================================
import io
from ..Address import Address
from .Control import Control
from .Flags import Flags

#===========================================================================

class OutAllLinkUpdate:
    """TODO: doc

    When sending, this will be 8 bytes long.  When receiving back from
    the modem, it will be 9 bytes (8+ack/nak).  
    """
    code = 0x6f
    msg_size = 12

    EXISTS = 0x00
    SEARCH = 0x01
    UPDATE = 0x20
    ADD_CONTROLLER = 0x40
    ADD_RESPONDER = 0x41
    DELETE = 0x80

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
        assert(raw[0] == 0x02 and raw[1] == OutAllLinkUpdate.code)

        # Make sure we have enough bytes to read the message.
        if OutAllLinkUpdate.msg_size > len(raw):
            return OutAllLinkUpdate.msg_size

        cmd = raw[2]
        ctrl = Control.read(raw, 3)
        group = raw[4]
        addr = Address.read(raw, 5)
        data = raw[8:11]
        is_ack = raw[12] == 0x06
        return OutAllLinkUpdate(cmd, ctrl, group, addr, data, is_ack)
        
    #-----------------------------------------------------------------------
    def __init__(self, cmd, ctrl, group, addr, data, is_ack=None):
        assert(cmd in [SEARCH, UPDATE, ADD_CONTROLLER, ADD_RESPONDER,
                           DELETE])
        assert(isinstance(ctrl, Control))
        
        self.cmd = cmd
        self.ctrl = ctrl
        self.group = group
        self.addr = addr
        self.data = data
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def raw(self):
        o = io.BytesIO(bytes([0x02, self.code]))
        o.write(self.cmd)
        o.write(self.ctrl.raw())
        o.write(self.group)
        o.write(self.addr.raw())
        o.write(self.data)
        return o.getvalue()

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
