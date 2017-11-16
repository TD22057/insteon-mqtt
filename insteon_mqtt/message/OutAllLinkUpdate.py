#===========================================================================
#
# Output insteon update all link database message.
#
#===========================================================================
import io
from ..Address import Address
from .DbFlags import DbFlags


class OutAllLinkUpdate:
    """TODO: doc

    When sending, this will be 8 bytes long.  When receiving back from
    the modem, it will be 9 bytes (8+ack/nak).

    The modem will respond with an echo/ACK of this message.
    """
    msg_code = 0x6f
    fixed_msg_size = 12

    EXISTS = 0x00
    SEARCH = 0x01
    UPDATE = 0x20
    ADD_CONTROLLER = 0x40
    ADD_RESPONDER = 0x41
    DELETE = 0x80

    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw)
        >= msg_size().

        Args:
           raw   (bytes): The current byte stream to read from.

        Returns:
           Returns the constructed OutAllLinkUpdate object.
        """
        assert len(raw) >= OutAllLinkUpdate.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == OutAllLinkUpdate.msg_code

        cmd = raw[2]
        flags = DbFlags.from_bytes(raw, 3)
        group = raw[4]
        addr = Address.from_bytes(raw, 5)
        data = raw[8:11]
        is_ack = raw[12] == 0x06
        return OutAllLinkUpdate(cmd, flags, group, addr, data, is_ack)

    #-----------------------------------------------------------------------
    def __init__(self, cmd, flags, group, addr, data, is_ack=None):
        """Constructor

        Args:
          cmd:     (int) Command byte.  See the class constants for valid
                   commands.
          flags:   (Flags) Message flags to send.
          group:   (int) All link group for the command.
          addr:    (Address) Address to send the command to.
          data:    (bytes) 3 byte data packet.
          is_ack:  (bool) True for ACK, False for NAK.  None for output
                   commands to the modem.
        """
        assert cmd in [self.SEARCH, self.UPDATE, self.ADD_CONTROLLER,
                       self.ADD_RESPONDER, self.DELETE]
        assert isinstance(flags, DbFlags)
        assert len(data) == 3

        self.cmd = cmd
        self.flags = flags
        self.group = group
        self.addr = addr
        self.data = data
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the message to a byte array.

        Returns:
           (bytes) Returns the message as bytes.
        """
        o = io.BytesIO(bytes([0x02, self.msg_code]))
        o.write(self.cmd)
        o.write(self.flags.to_bytes())
        o.write(self.group)
        o.write(self.addr.to_bytes())
        o.write(self.data)
        return o.getvalue()

    #-----------------------------------------------------------------------
    def __str__(self):
        lbl = {
            self.EXISTS : "EXISTS",
            self.SEARCH : "SEARCH",
            self.UPDATE : "UPDATE",
            self.ADD_CONTROLLER : "ADD_CTRL",
            self.ADD_RESPONDER : "ADD_RESP",
            self.DELETE : "DELETE",
            }

        return "OutAllLinkUpdate: %s grp: %s %s: %s" % \
            (self.addr, self.group, lbl[self.cmd], self.is_ack)

    #-----------------------------------------------------------------------

#===========================================================================
