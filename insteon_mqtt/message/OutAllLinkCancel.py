#===========================================================================
#
# Output insteon all link cancel message.
#
#===========================================================================


class OutAllLinkCancel:
    """Cancel PLM all linking mode.

    This is sent to cancel the all link mode on the PLM modem.  The
    modem will respond with an echo/ACK of this message.
    """
    msg_code = 0x65
    fixed_msg_size = 3

    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw)
        >= msg_size().

        Args:
           raw   (bytes): The current byte stream to read from.

        Returns:
           Returns the constructed message object.
        """
        assert len(raw) >= OutAllLinkCancel.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == OutAllLinkCancel.msg_code

        is_ack = raw[2] == 0x06
        return OutAllLinkCancel(is_ack)

    #-----------------------------------------------------------------------
    def __init__(self, is_ack=None):
        """Constructor

        Args:
          is_ack:  (bool) True for ACK, False for NAK.  None for output
                   commands to the modem.
        """
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the message to a byte array.

        Returns:
           (bytes) Returns the message as bytes.
        """
        return bytes([0x02, self.msg_code])

    #-----------------------------------------------------------------------
    def __str__(self):
        return "All link cancel: ack: %s" % self.is_ack

    #-----------------------------------------------------------------------

#===========================================================================
