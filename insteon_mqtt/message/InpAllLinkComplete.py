#===========================================================================
#
# Input insteon all link complete message.
#
#===========================================================================
from ..Address import Address

#===========================================================================

class InpAllLinkComplete:
    """All linking complete.

    This is sent from the PLM modem to the host when linking between
    the PLM modem and a device is completed.
    """
    msg_code = 0x53
    fixed_msg_size = 10

    RESPONDER = 0x01
    CONTROLLER = 0x01
    DELETE = 0xff

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
        assert len(raw) >= InpAllLinkComplete.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == InpAllLinkComplete.msg_code

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
        """Constructor

        Args:
          link:         Link command flag.  InpAllLinkComplete.RESPONDER,
                        InpAllLinkComplete.CONTROLLER, or
                        InpAllLinkComplete.DELETE.
          group:        (int) The all link group of the link.
          addr:         (Address) The address of the device being linked.
          dev_cat:      (int) device category.
          dev_subcat:   (int) Device subcategory.
          firmware:     (int) Firmware revision.
        """
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
