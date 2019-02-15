#===========================================================================
#
# Output insteon start all link mode message.
#
#===========================================================================
import enum
from .Base import Base


class OutModemLinking(Base):
    """Begin all linking command message.

    This puts the modem into linking mode (like holding set for 3 sec).
    """
    msg_code = 0x64
    fixed_msg_size = 5

    # Valid command codes
    class Cmd(enum.IntEnum):
        RESPONDER = 0x00  # modem is responder
        CONTROLLER = 0x01  # modem is controller
        EITHER = 0x03  # modem 1st: modem is ctrl; device 1st: modem is resp
        DELETE = 0xff

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
          Returns the constructed OutAllLinkStart object.
        """
        assert len(raw) >= cls.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == cls.msg_code

        cmd = cls.Cmd(raw[2])
        group = raw[3]
        is_ack = raw[4] == 0x06
        return OutModemLinking(cmd, group, is_ack)

    #-----------------------------------------------------------------------
    def __init__(self, cmd, group, is_ack=None):
        """Constructor

        Args:
          cmd (int):  OutAllLinkStart.RESPONDER, OutAllLinkStart.CONGTROLLER,
              or OutAllLinkStart.DELETE command code.
          group (int):  The group to link.
          is_ack (bool):  True for ACK, False for NAK.  None for output
                 commands to the modem.
        """
        super().__init__()

        self.cmd = self.Cmd(cmd)
        self.group = group
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the message to a byte array.

        Returns:
          bytes:  Returns the message as bytes.
        """
        return bytes([0x02, self.msg_code, self.cmd.value, self.group])

    #-----------------------------------------------------------------------
    def __str__(self):
        ack = "" if self.is_ack is None else " ack: %s" % self.is_ack
        return "Modem linking: grp: %s %s%s" % (self.group, self.cmd, ack)

    #-----------------------------------------------------------------------

#===========================================================================
