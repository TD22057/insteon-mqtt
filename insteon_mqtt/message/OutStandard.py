#===========================================================================
#
# Output insteon standard and extended message.
#
#===========================================================================
import io
from ..Address import Address
from .Flags import Flags


class OutStandard:
    """Direct, standard message from host->PLM.

    When sending, this will be 8 bytes long.  When receiving back from
    the modem, it will be 9 bytes (8+ack/nak).  The from_bytes()
    function can also return an OutExtended if the extended message
    bit is set.

    The response from the modem to this message will depend on the
    cmd1/cmd2 command field inputs.
    """
    msg_code = 0x62
    fixed_msg_size = 9

    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(raw):
        """Read the message from a byte stream.

        You cannot pass the output of to_bytes() to this.  to_bytes()
        is used to output to the PLM but the modem sends back the same
        message with an extra ack byte which this function can read.

        This should only be called if raw[1] == msg_code and len(raw)
        >= msg_size().

        Args:
           raw   (bytes): The current byte stream to read from.

        Returns:
           Returns the constructed OutStandard or OutExtended object.
        """
        assert len(raw) >= OutStandard.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == OutStandard.msg_code

        # Read the first 9 bytes into a standard message.
        to_addr = Address.from_bytes(raw, 2)
        flags = Flags.from_bytes(raw, 5)
        cmd1 = raw[6]
        cmd2 = raw[7]

        # If this is standard message, built it and return.
        if not flags.is_ext:
            is_ack = raw[8] == 0x06
            return OutStandard(to_addr, flags, cmd1, cmd2, is_ack)

        # Read the extended message payload.
        assert len(raw) >= OutExtended.fixed_msg_size
        data = raw[8:22]
        is_ack = raw[22] == 0x06
        return OutExtended(to_addr, flags, cmd1, cmd2, data, is_ack)

    #-----------------------------------------------------------------------
    @staticmethod
    def direct(to_addr, cmd1, cmd2):
        """Construct a direct, standard message

        Args:
          to_addr:  (Address) The adddress to send the commadn to.
          cmd1:     (int) The command 1 field to set.
          cmd2:     (int) The command 2 field to set.

        Returns:
          Returns the created OutStandard message.
        """
        flags = Flags(Flags.DIRECT, is_ext=False)
        return OutStandard(to_addr, flags, cmd1, cmd2)

    #-----------------------------------------------------------------------
    def __init__(self, to_addr, flags, cmd1, cmd2, is_ack=None):
        """General constructor

        Args:
          to_addr:  (Address) The adddress to send the commadn to.
          flags:    (Flags) Message flags to use.
          cmd1:     (int) The command 1 field to set.
          cmd2:     (int) The command 2 field to set.
          is_ack:   (bool) True for ACK, False for NAK.  None for output
                    commands to the modem.
        """
        assert isinstance(flags, Flags)

        self.to_addr = to_addr
        self.flags = flags
        self.cmd1 = cmd1
        self.cmd2 = cmd2
        self.is_ack = is_ack

    #-----------------------------------------------------------------------
    def msg_size(self, raw):
        """Return the message size in bytes.

        Standard and Extended messages depend on the message flags
        inside the message so some types will need to parse part of
        the byte array to figure out the total size.

        Args:
           raw   (bytes): The current byte stream to read from.

        Returns:
           Returns the constructed message object.
        """
        assert len(raw) >= OutStandard.fixed_msg_size

        # Read the message flags first to see if we have an extended
        # message.  If we do, make sure we have enough bytes.
        flags = Flags.from_bytes(raw, 5)
        if not flags.is_ext:
            return OutStandard.fixed_msg_size
        else:
            return OutExtended.fixed_msg_size

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the message to a byte array.

        Returns:
           (bytes) Returns the message as bytes.
        """
        o = io.BytesIO()
        o.write(bytes([0x02, self.msg_code]))
        o.write(self.to_addr.to_bytes())
        o.write(self.flags.to_bytes())
        o.write(bytes([self.cmd1, self.cmd2]))
        return o.getvalue()

    #-----------------------------------------------------------------------
    def __str__(self):
        ack = "" if self.is_ack is None else " ack: %s" % self.is_ack
        return "Std: %s, %s, %02x %02x%s" % \
            (self.to_addr, self.flags, self.cmd1, self.cmd2, ack)

    #-----------------------------------------------------------------------

#===========================================================================


class OutExtended(OutStandard):
    """Direct extended message from host->PLM.

    When sending, this will be 22 bytes long.  When receiving back
    from the modem, it will be 23 bytes (22+ack/nak).  Since this hsa
    the same message code as OutStandard, use OutStandard.from_bytes()
    to read either type.

    The response from the modem to this message will depend on the
    cmd1/cmd2 command field inputs.
    """
    fixed_msg_size = 23

    #-----------------------------------------------------------------------
    @staticmethod
    def direct(to_addr, cmd1, cmd2, data):
        """Construct a direct, extended message

        Args:
          to_addr:  (Address) The adddress to send the commadn to.
          cmd1:     (int) The command 1 field to set.
          cmd2:     (int) The command 2 field to set.
          data:     (byte) The extended data array of 14 bytes.

        Returns:
          Returns the created OutStandard message.
        """
        flags = Flags(Flags.DIRECT, is_ext=True)
        return OutExtended(to_addr, flags, cmd1, cmd2, data)

    #-----------------------------------------------------------------------
    def __init__(self, to_addr, flags, cmd1, cmd2, data, is_ack=None):
        """General constructor

        Args:
          to_addr:  (Address) The adddress to send the commadn to.
          flags:    (Flags) Message flags to use.
          cmd1:     (int) The command 1 field to set.
          cmd2:     (int) The command 2 field to set.
          data:     (byte) The extended data array of 14 bytes.
          is_ack:   (bool) True for ACK, False for NAK.  None for output
                    commands to the modem.
        """
        assert len(data) == 14

        super().__init__(to_addr, flags, cmd1, cmd2, is_ack)
        self.data = data

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the message to a byte array.

        Returns:
           (bytes) Returns the message as bytes.
        """
        return OutStandard.to_bytes(self) + self.data

    #-----------------------------------------------------------------------
    def __str__(self):
        ack = "" if self.is_ack is None else " ack: %s" % self.is_ack

        o = io.StringIO()
        o.write("Ext: %s, %s, %02x %02x%s\n" %
                (self.to_addr, self.flags, self.cmd1, self.cmd2, ack))
        for i in self.data:
            o.write("%02x " % i)
        return o.getvalue()

    #-----------------------------------------------------------------------

#===========================================================================
