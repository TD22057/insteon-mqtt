#===========================================================================
#
# Output insteon all link command message.
#
#===========================================================================
from .Base import Base


class OutModemScene(Base):
    """Trigger a virtual PLM modem scene activation.

    This triggers a PLM modem scene.  Any devices linked to the modem with
    this group ID will change state.  This basically triggers the virtual
    scenes that can be defined on the modem.
    """
    msg_code = 0x61
    fixed_msg_size = 6

    #-----------------------------------------------------------------------
    @classmethod
    def from_bytes(cls, raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw) >=
        msg_size().

        You cannot pass the output of to_bytes() to this.  to_bytes() is used
        to output to the PLM but the modem sends back the same message with
        an extra ack byte which this function can read.

        Args:
          raw (bytes):  The current byte stream to read from.

        Returns:
          Returns the constructed message object.
        """
        assert len(raw) >= cls.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == cls.msg_code

        group = raw[2]
        cmd1 = raw[3]
        cmd2 = raw[4]
        is_ack = raw[5] == 0x06
        return OutModemScene(group, cmd1, cmd2, is_ack)

    #-----------------------------------------------------------------------
    def __init__(self, group, cmd1, cmd2, is_ack=None):
        """Constructor

        Args:
          group (int):  The group to send the command for.
          cmd1 (int):  The command 1 field.
          cmd2 (int):  The command 2 field.
          is_ack (bool): True for ACK, False for NAK.  None for output
                 commands to the modem.
        """
        super().__init__()

        self.group = group
        self.cmd1 = cmd1
        self.cmd2 = cmd2
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the message to a byte array.

        Returns:
          bytes:  Returns the message as bytes.
        """
        return bytes([0x02, self.msg_code,
                      self.group, self.cmd1, self.cmd2])

    #-----------------------------------------------------------------------
    def __str__(self):
        ack = "" if self.is_ack is None else " ack: %s" % self.is_ack
        return ("Modem Scene: grp: %s cmd: %#04x %#04x%s" %
                (self.group, self.cmd1, self.cmd2, ack))

    #-----------------------------------------------------------------------

#===========================================================================
