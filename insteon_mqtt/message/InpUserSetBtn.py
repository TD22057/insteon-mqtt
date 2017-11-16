#===========================================================================
#
# PLM->host standard direct message
#
#===========================================================================


class InpUserSetBtn:
    """TODO
    """
    code = 0x54
    msg_size = 3

    events = {
        0x02 : 'SET_TAPPED',
        0x03 : 'SET_HOLD',
        0x04 : 'SET_RELEASED',
        0x12 : 'BTN2_TAPPED',
        0x13 : 'BTN2_HOLD',
        0x14 : 'BTN2_RELEASED',
        0x22 : 'BTN3_TAPPED',
        0x23 : 'BTN3_HOLD',
        0x24 : 'BTN3_RELEASED',
        }

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
        assert raw[0] == 0x02 and raw[1] == InpUserSetBtn.code

        # Make sure we have enough bytes to read the message.
        if InpUserSetBtn.msg_size > len(raw):
            return InpUserSetBtn.msg_size

        event = InpUserSetBtn.events.get(raw[2], 'UNKNOWN')
        return InpUserSetBtn(event)

    #-----------------------------------------------------------------------
    def __init__(self, event):
        self.event = event

    #-----------------------------------------------------------------------
    def __str__(self):
        return "Set btn: %s" % InpUserSetBtn.events[self.event]

    #-----------------------------------------------------------------------

#===========================================================================
