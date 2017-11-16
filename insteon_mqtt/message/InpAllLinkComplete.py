#===========================================================================
#
# PLM->host standard direct message
#
#===========================================================================
from ..Address import Address

#===========================================================================

class InpAllLinkComplete:
    """TODO
    """
    code = 0x53
    msg_size = 10

    RESPONDER = 0x01
    CONTROLLER = 0x01
    DELETE = 0xff

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
        assert len(raw) >= 2
        assert raw[0] == 0x02 and raw[1] == InpAllLinkComplete.code

        # Make sure we have enough bytes to read the message.
        if InpAllLinkComplete.msg_size > len(raw):
            return InpAllLinkComplete.msg_size

        link = raw[2]
        group = raw[3]
        addr = Address.from_bytes(raw, 4)
        dev_cat = raw[7]
        dev_subcat = raw[8]
        firmware = raw[9]
        return InpAllLinkComplete(link, group, addr, dev_cat, dev_subcat,
                                  firmware)

    #-----------------------------------------------------------------------
    def __init__(self, link, group, addr, dev_cat, dev_subcat, firmware):
        self.link = link
        self.plm_responder = link == self.RESPONDER
        self.plm_controller = link == self.CONTROLLER
        self.is_delete = link == self.DELETE
        self.group = group
        self.addr = addr
        self.dev_cat = dev_cat
        self.dev_subcat = dev_subcat
        self.firmware = firmware

    #-----------------------------------------------------------------------
    def __str__(self):
        lbl = {
            self.RESPONDER : 'RESP',
            self.CONTROLLER : 'CTRL',
            self.DELETE : 'DEL',
            }
        return "All link done: %s grp: %d %s cat: %#04x %#04x %#04x" % \
            (self.addr, self.group, lbl[self.link], self.dev_cat,
             self.dev_subcat, self.firmware)

    #-----------------------------------------------------------------------

#===========================================================================
