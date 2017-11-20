#===========================================================================
#
# Output insteon start all link mode message.
#
#===========================================================================
from .Base import Base


class OutAllLinkStart(Base):
    """Begin all linking command message.
    """
    msg_code = 0x64
    fixed_msg_size = 5

    RESPONDER = 0x01
    CONTROLLER = 0x03
    DELETE = 0xff

    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw)
        >= msg_size().

        You cannot pass the output of to_bytes() to this.  to_bytes()
        is used to output to the PLM but the modem sends back the same
        message with an extra ack byte which this function can read.

        Args:
           raw   (bytes): The current byte stream to read from.

        Returns:
           Returns the constructed OutAllLinkStart object.
        """
        assert len(raw) >= OutAllLinkStart.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == OutAllLinkStart.msg_code

        link = raw[2]
        group = raw[3]
        is_ack = raw[4] == 0x06
        return OutAllLinkStart(link, group, is_ack)

    #-----------------------------------------------------------------------
    def __init__(self, link, group, is_ack=None):
        """Constructor

        Args:
          link:    (int) OutAllLinkStart.RESPONDER,
                   OutAllLinkStart.CONGTROLLER, or OutAllLinkStart.DELETE
                   command code.
          group:   (int) The group to link.
          is_ack:  (bool) True for ACK, False for NAK.  None for output
                   commands to the modem.
        """
        super().__init__()

        assert(link == self.RESPONDER or link == self.CONTROLLER or
               link == self.DELETE)

        self.link = link
        self.plm_responder = link == self.RESPONDER
        self.plm_controller = link == self.CONTROLLER
        self.is_delete = link == self.DELETE
        self.group = group
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the message to a byte array.

        Returns:
           (bytes) Returns the message as bytes.
        """
        return bytes([0x02, self.msg_code, self.link, self.group])

    #-----------------------------------------------------------------------
    def __str__(self):
        lbl = {
            self.RESPONDER : 'RESP',
            self.CONTROLLER : 'CTRL',
            self.DELETE : 'DEL',
            }

        return "All link start: grp: %s %s ack: %s" % \
            (self.group, lbl[self.link], self.is_ack)

    #-----------------------------------------------------------------------

#===========================================================================
