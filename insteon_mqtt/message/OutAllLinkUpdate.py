#===========================================================================
#
# Output insteon update all link database message.
#
#===========================================================================
import enum
import io
from ..Address import Address
from .Base import Base
from .DbFlags import DbFlags


class OutAllLinkUpdate(Base):
    """Modem database all linking database update message.

    This message is used to change (add, edit, delete) an entry in the
    modem's all link database.  After sending, the modem should ACK this back
    with the result (ACK = success, NAK = failure).
    """
    msg_code = 0x6f
    fixed_msg_size = 12

    # The modem developers guide is wrong regarding much of this.  There are
    # no alternative commands such as 'add or modify' as stated in the
    # document. All commands do one function only.  Additionally, the entry
    # matching includes the ctrl/resp status except on Delete(which requires
    # the db_flags to be 0x00).
    #
    # The following is what each control code does based on testing.
    # 0x00 - FIND FIRST - Searches for an entry matching addr, group, but not
    #        ctrl/resp, the db_flags can be set, but will be ignored.  Will
    #        produce an ACK if a matching entry is found, followed by a
    #        InpAllLinkRec containing the entry.
    # 0x01 - FIND NEXT - Searches for the next entry matching the addr,
    #        group, but not ctrl/resp, previously searched by the 0x00 FIND
    #        FIRST command above. The db_flags can be set, but will be ignored.
    #        Will produce an ACK if a matching entry is found, followed by a
    #        InpAllLinkRec containing the entry.
    # 0x20 - UPDATE - Searches for an entry matching addr, group, AND ctrl/resp
    #        and updates the Data1-3 values for this entry based on what was
    #        passed.  Will return NACK if no matching entry is found
    # 0x40 - ADD_CONTROLLER - Adds the controller record included in the cmd.
    #        Will produce a NACK if a controller record matching the addr,
    #        group, AND ctrl/resp already exists.Will also nack if the entry
    #        in the command is not a controller entry.
    # 0x41 - ADD_RESPONDER - Adds the responder record included in the cmd.
    #        Will produce a NACK if a responder record matching the addr,
    #        group, AND ctrl/resp already exists.  Will also nack if the entry
    #        in the command is not a responder entry.
    # 0x80 - DELETE - Searches for an entry matching addr, group, but not
    #        ctrl/resp, indeed the db_flags need to be 0x00 otherwise the
    #        search will NACK.  The first matching entry (ctrl or resp) will
    #        be deleted. If no entry can be found a NACK will be returned.

    # Valid command codes
    class Cmd(enum.IntEnum):
        EXISTS = 0x00
        SEARCH = 0x01
        UPDATE = 0x20
        ADD_CONTROLLER = 0x40
        ADD_RESPONDER = 0x41
        DELETE = 0x80

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
          Returns the constructed OutAllLinkUpdate object.
        """
        assert len(raw) >= cls.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == cls.msg_code

        cmd = cls.Cmd(raw[2])
        db_flags = DbFlags.from_bytes(raw, 3)
        group = raw[4]
        addr = Address.from_bytes(raw, 5)
        data = raw[8:11]
        is_ack = raw[11] == 0x06
        return OutAllLinkUpdate(cmd, db_flags, group, addr, data, is_ack)

    #-----------------------------------------------------------------------
    def __init__(self, cmd, db_flags, group, addr, data=None, is_ack=None):
        """Constructor

        Args:
          cmd (Cmd):  Command byte.  See the OutAllLinkUpdate.Cmd enumeration
              for valid values.
          db_flags (Flags):  Message flags to send.
          group (int):  All link group for the command.
          addr (Address):  Address to send the command to.
          data (bytes):  3 byte data packet.  If None, three 0x00 are sent.
          is_ack (bool): True for ACK, False for NAK.  None for output
                 commands to the modem.
        """
        super().__init__()

        assert isinstance(db_flags, DbFlags)
        assert data is None or len(data) == 3

        self.cmd = self.Cmd(cmd)
        self.db_flags = db_flags
        self.group = group
        self.addr = addr
        self.data = data if data is not None else bytes(3)
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the message to a byte array.

        Returns:
          bytes:  Returns the message as bytes.
        """
        o = io.BytesIO()
        o.write(bytes([0x02, self.msg_code, self.cmd.value]))
        # db_flags must be 0x00 for a modem delete
        o.write(self.db_flags.to_bytes(
            modem_delete=self.cmd == self.Cmd.DELETE))
        o.write(bytes([self.group]))
        o.write(self.addr.to_bytes())
        o.write(self.data)
        return o.getvalue()

    #-----------------------------------------------------------------------
    def __str__(self):
        ack = "" if self.is_ack is None else " ack: %s" % self.is_ack
        return ("OutAllLinkUpdate: %s grp: %s %s%s" %
                (self.addr, self.group, self.cmd, ack))

    #-----------------------------------------------------------------------

#===========================================================================
