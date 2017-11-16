#===========================================================================
#
# Host->PLM standard direct message
#
#===========================================================================


class OutAllLinkCancel:
    """Direct, standard message from host->PLM.

    When sending, this will be 8 bytes long.  When receiving back from
    the modem, it will be 9 bytes (8+ack/nak).
    """
    code = 0x65
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
           that need to be in the message to finish reading it.
           Otherwise the read message is returned.  This will return
           either an OutStandard or OutExtended message.
        """
        assert len(raw) >= 2
        assert raw[0] == 0x02 and raw[1] == OutAllLinkCancel.code

        # Make sure we have enough bytes to read the message.
        if OutAllLinkCancel.msg_size > len(raw):
            return OutAllLinkCancel.msg_size

        is_ack = raw[2] == 0x06
        return OutAllLinkCancel(is_ack)

    #-----------------------------------------------------------------------
    def __init__(self, is_ack=None):
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def to_bytes(self):
        return bytes([0x02, self.code])

    #-----------------------------------------------------------------------
    def __str__(self):
        return "All link cancel: ack: %s" % self.is_ack

    #-----------------------------------------------------------------------

#===========================================================================
