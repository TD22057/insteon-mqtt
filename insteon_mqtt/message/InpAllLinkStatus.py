#===========================================================================
#
# PLM->host standard direct message
#
#===========================================================================


class InpAllLinkStatus:
    """TODO
    """
    code = 0x58
    msg_size = 3

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
        assert raw[0] == 0x02 and raw[1] == InpAllLinkStatus.code

        # Make sure we have enough bytes to read the message.
        if InpAllLinkStatus.msg_size > len(raw):
            return InpAllLinkStatus.msg_size

        is_ack = raw[2] == 0x06
        return InpAllLinkStatus(is_ack)

    #-----------------------------------------------------------------------
    def __init__(self, is_ack):
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def __str__(self):
        return "All link status ack: %d" % self.is_ack

    #-----------------------------------------------------------------------

#===========================================================================
