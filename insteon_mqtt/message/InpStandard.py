#===========================================================================
#
# Input insteon standard and extended message.
#
#===========================================================================
import io
import time
from ..Address import Address
from .Base import Base
from .Flags import Flags


class InpStandard(Base):
    """Direct, standard message.

    This is sent from the PLM modem to the host when various conditions
    happen.  Standard messages are general purpose - they can contain a lot
    of different data and it's up to the message handler to interpret the
    results.
    """
    # pylint: disable=abstract-method

    msg_code = 0x50
    fixed_msg_size = 11

    #-----------------------------------------------------------------------
    @classmethod
    def from_bytes(cls, raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw) >=
        msg_size().

        Args:
          raw (bytes):  The current byte stream to read from.

        Returns:
          Returns the constructed message object.
        """
        assert len(raw) >= InpStandard.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == InpStandard.msg_code

        # Read the message flags first to see if we have an extended message.
        # If we do, make sure we have enough bytes.
        from_addr = Address.from_bytes(raw, 2)
        to_addr = Address.from_bytes(raw, 5)
        flags = Flags.from_bytes(raw, 8)
        cmd1 = raw[9]
        cmd2 = raw[10]
        return InpStandard(from_addr, to_addr, flags, cmd1, cmd2)

    #-----------------------------------------------------------------------
    def __init__(self, from_addr, to_addr, flags, cmd1, cmd2):
        """Constructor

        Args:
          from_addr (Address):  The from device address.
          to_addr (Address):  The to device address.
          flags (Flags):  The message flags.
          cmd1 (int):  The command 1 byte.
          cmd2 (int):  The command 2 byte.
        """
        super().__init__()

        assert isinstance(flags, Flags)

        self.from_addr = from_addr
        self.to_addr = to_addr
        self.flags = flags
        self.cmd1 = cmd1
        self.cmd2 = cmd2
        self.group = None
        if self.flags.is_broadcast:
            self.group = self.to_addr.ids[2]
        elif (self.flags.type == Flags.Type.ALL_LINK_CLEANUP or
              self.flags.type == Flags.Type.CLEANUP_ACK):
            self.group = self.cmd2

        # This is the time by which the final hop would arrive, used to
        # detect duplicates.  87 msec is empirical and was found to be an OK
        # value to use with standard length messages in other Insteon
        # software (misterhouse?)
        self.expire_time = time.time() + self.flags.hops_left * 0.087

    #-----------------------------------------------------------------------
    def nak_str(self):
        """Get NAK Explanation String

        Cmd2 of an I2CS NAK response may contain an explanation for the nak,
        according to Insteon these are:

            0xFF = Sender’s device ID not in responder’s database
            0xFE = Load sense detects no load
            0xFD = Checksum is incorrect
            0xFC = Pre NAK in case database search takes too long
            0xFB = illegal value in command

        Returns:
          str:  Returns a string NAK explanation if one exists otherwise an
                empty string
        """
        ret = ""
        naks = {
            0xFF: "Senders ID not in responders db. Try linking again.",
            0xFE: "Load sense detects no load",
            0xFD: "Checksum is incorrect",
            0xFC: "Pre NAK in case database search takes too long",
            0xFB: "Illegal value in command"
        }
        if (self.flags.type == Flags.Type.DIRECT_NAK and
                self.cmd2 in naks.keys()):
            ret = naks[self.cmd2]
        return ret

    #-----------------------------------------------------------------------
    def __str__(self):
        if self.group is None:
            return ("Std: %s->%s %s cmd: %02x %02x" %
                    (self.from_addr, self.to_addr, self.flags, self.cmd1,
                     self.cmd2))
        else:
            return ("Std: %s %s grp: %02x cmd: %02x %02x" %
                    (self.from_addr, self.flags, self.group, self.cmd1,
                     self.cmd2))

    #-----------------------------------------------------------------------
    def __eq__(self, rhs):
        """Checks for message for equality.

        This ignores differences in the hops_left and max_hops field, but if
        a message is otherwise the same, it is a equal.

        Args:
          rhs (Message):  The message to compare to this one.

        Returns:
          bool:  True if the message is a duplicate false otherwise.
        """
        if not isinstance(rhs, InpStandard):
            return False

        return (self.from_addr == rhs.from_addr and
                self.flags == rhs.flags and
                self.group == rhs.group and
                self.cmd1 == rhs.cmd1 and
                self.cmd2 == rhs.cmd2)

    #-----------------------------------------------------------------------

#===========================================================================


class InpExtended(Base):
    """Direct, extended message from PLM->host.

    The extended message is used by specialized devices to report state as
    well as when a device reports it's all link database records.
    """
    # pylint: disable=abstract-method

    msg_code = 0x51
    fixed_msg_size = 25

    #-----------------------------------------------------------------------
    @classmethod
    def from_bytes(cls, raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw) >=
        msg_size().

        Args:
          raw (bytes):  The current byte stream to read from.

        Returns:
          Returns the constructed OutStandard or OutExtended object.
        """
        assert len(raw) >= InpExtended.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == InpExtended.msg_code

        from_addr = Address.from_bytes(raw, 2)
        to_addr = Address.from_bytes(raw, 5)
        flags = Flags.from_bytes(raw, 8)
        cmd1 = raw[9]
        cmd2 = raw[10]
        data = raw[11:25]
        return InpExtended(from_addr, to_addr, flags, cmd1, cmd2, data)

    #-----------------------------------------------------------------------
    def __init__(self, from_addr, to_addr, flags, cmd1, cmd2, data):
        """Constructor

        Args:
          from_addr (Address):  The from device address.
          to_addr (Address):  The to device address.
          flags (Flags):  The message flags.
          cmd1 (int):  The command 1 byte.
          cmd2 (int):  The command 2 byte.
          data (bytes):  14 byte extended data array.
        """
        super().__init__()

        assert len(data) == 14

        self.from_addr = from_addr
        self.to_addr = to_addr
        self.flags = flags
        self.cmd1 = cmd1
        self.cmd2 = cmd2
        self.data = data
        self.group = None
        if self.flags.is_broadcast:
            self.group = self.to_addr.ids[2]
        elif (self.flags.type == Flags.Type.ALL_LINK_CLEANUP or
              self.flags.type == Flags.Type.CLEANUP_ACK):
            self.group = self.cmd2

        # This is the time by which the final hop would arrive, used to
        # detect duplicates.  183 msec is empirical and was found to be an OK
        # value to use with extended length messages in other Insteon
        # software (misterhouse?)
        self.expire_time = time.time() + self.flags.hops_left * 0.183

    #-----------------------------------------------------------------------
    def __str__(self):
        o = io.StringIO()
        if self.group is None:
            o.write("Ext: %s->%s %s cmd: %02x %02x\n" %
                    (self.from_addr, self.to_addr, self.flags, self.cmd1,
                     self.cmd2))
        else:
            o.write("Ext: %s %s grp: %02x cmd: %02x %02x" %
                    (self.from_addr, self.flags, self.group, self.cmd1,
                     self.cmd2))

        for i in self.data:
            o.write("%02x " % i)
        return o.getvalue()

    #-----------------------------------------------------------------------
    def __eq__(self, rhs):
        """Checks for message for equality.

        This ignores differences in the hops_left and max_hops field, but if
        a message is otherwise the same, it is a equal.

        Args:
          rhs (Message):  The message to compare to this one.

        Returns:
          bool:  True if the message is a duplicate false otherwise.
        """
        if not isinstance(rhs, InpExtended):
            return False

        return (self.from_addr == rhs.from_addr and
                self.flags == rhs.flags and
                self.group == rhs.group and
                self.cmd1 == rhs.cmd1 and
                self.cmd2 == rhs.cmd2 and
                self.data == rhs.data)

    #-----------------------------------------------------------------------

#===========================================================================
