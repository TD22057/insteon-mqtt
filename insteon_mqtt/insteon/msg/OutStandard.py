#===========================================================================
#
# Host->PLM standard direct message
#
#===========================================================================
import io
from ..Address import Address
from .Flags import Flags

#===========================================================================

class OutStandard:
    """Direct, standard message from host->PLM.

    When sending, this will be 8 bytes long.  When receiving back from
    the modem, it will be 9 bytes (8+ack/nak).  
    """
    code = 0x62
    msg_size = 9

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
        assert(raw[0] == 0x02 and raw[1] == OutStandard.code)

        # Make sure we have enough bytes to read the message.
        if OutStandard.msg_size > len(raw):
            return OutStandard.msg_size

        # Read the message flags first to see if we have an extended
        # message.  If we do, make sure we have enough bytes.
        flags = Flags.read(raw, 5)
        if flags.is_ext:
            if OutExtended.msg_size > len(raw):
                return OutExtended.msg_size
        
        # Read the first 9 bytes into a standard message.
        to_addr = Address.read(raw, 2)
        cmd1 = raw[6]
        cmd2 = raw[7]

        # If this is standard message, built it and return.
        if not flags.is_ext:
            is_ack = raw[8] == 0x06
            return OutStandard(to_addr, flags, cmd1, cmd2, is_ack)

        # Read the extended message payload.
        data = raw[8:22]
        is_ack = raw[22] == 0x06
        return OutExtended(to_addr, flags, cmd1, cmd2, data, is_ack)
        
    #-----------------------------------------------------------------------
    @staticmethod
    def direct(to_addr, cmd1, cmd2):
        flags = Flags(Flags.DIRECT, is_ext=False)
        return OutStandard(to_addr, flags, cmd1, cmd2)
        
    #-----------------------------------------------------------------------
    def __init__(self, to_addr, flags, cmd1, cmd2, is_ack=None):
        assert(isinstance(flags, Flags))
        
        self.to_addr = to_addr
        self.flags = flags
        self.cmd1 = cmd1
        self.cmd2 = cmd2
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def raw(self):
        o = io.BytesIO()
        o.write(bytes([0x02, self.code]))
        o.write(self.to_addr.raw())
        o.write(self.flags.raw())
        o.write(bytes([self.cmd1, self.cmd2]))
        return o.getvalue()

    #-----------------------------------------------------------------------
    def __str__(self):
        return "Std: %s, %s, %02x %02x ack: %s" % \
            (self.to_addr, self.flags, self.cmd1, self.cmd2, self.is_ack)

    #-----------------------------------------------------------------------
    
#===========================================================================
class OutExtended (OutStandard):
    msg_size = 23
    
    #-----------------------------------------------------------------------
    @staticmethod
    def direct(to_addr, cmd1, cmd2, data):
        flags = Flags(Flags.DIRECT, is_ext=False)
        return OutStandard(to_addr, flags, cmd1, cmd2, data)
        
    #-----------------------------------------------------------------------
    def __init__(self, to_addr, flags, cmd1, cmd2, data, is_ack=None):
        assert(len(data) == 14)
        
        OutStandard.__init__(self, to_addr, flags, cmd1, cmd2, is_ack )
        self.data = data
    
    #-----------------------------------------------------------------------
    def raw(self):
        return OutStandard.raw(self) + self.data

    #-----------------------------------------------------------------------
    def __str__(self):
        o = io.StringIO()
        o.write("Ext: %s, %s, %02x %02x ack: %s\n" % 
                (self.to_addr, self.flags, self.cmd1, self.cmd2, self.is_ack))
        for i in self.data:
            o.write("%02x " % i )
        return o.getvalue()
    
    #-----------------------------------------------------------------------

#===========================================================================
