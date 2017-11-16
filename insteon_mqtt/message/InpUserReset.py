#===========================================================================
#
# PLM->host standard direct message
#
#===========================================================================


class InpUserReset:
    """TODO
    """
    code = 0x55
    msg_size = 2

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
        assert raw[0] == 0x02 and raw[1] == InpUserReset.code

        # Make sure we have enough bytes to read the message.
        if InpUserReset.msg_size > len(raw):
            return InpUserReset.msg_size

        return InpUserReset()

    #-----------------------------------------------------------------------
    def __init__(self):
        pass

    #-----------------------------------------------------------------------
    def __str__(self):
        return "User reset"

    #-----------------------------------------------------------------------

#===========================================================================
