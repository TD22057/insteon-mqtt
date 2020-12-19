#===========================================================================
#
# Base message class
#
#===========================================================================
import enum

class Base:
    """Base message class

    This sets the basic message API that all the classes support.  If the
    message is fixed length, set fixed_msg_size, otherwise implement
    msg_size().
    """
    msg_code = None  # set to the message ID byte.

    # Read message size (including ack/nak byte).  Derived types should set
    # this if the message has fixed size otherwise implement msg_size().
    fixed_msg_size = None

    # Cmd types used in InpStandard OutStandard
    # Used to make reading the code easier. I am not sure that the insteon
    # specification is always consistent so be careful using these
    class CmdType(enum.IntEnum):
        ASSIGN_TO_GROUP = 0x01
        DELETE_FROM_GROUP = 0x02
        LINK_CLEANUP_REPORT = 0x06
        LINKING_MODE = 0x09
        UNLINKING_MODE = 0x0A
        GET_ENGINE_VERSION = 0x0D
        PING = 0x0F
        ID_REQUEST = 0x10
        ON_FAST = 0x12
        OFF_FAST = 0x14
        START_MANUAL_CHANGE = 0x17
        STOP_MANUAL_CHANGE = 0x18
        STATUS_REQUEST = 0x19
        GET_OPERATING_FLAGS = 0x1f
        SET_OPERATING_FLAGS = 0x20
        DO_READ_EE = 0x24
        REMOTE_SET_BUTTON_TAP = 0x25
        SET_LED_STATUS = 0x27
        SET_ADDRESS_MSB = 0x28
        POKE = 0x29
        POKE_EXTENDED = 0x2a
        PEEK = 0x2b
        PEEK_INTERNAL = 0x2c
        POKE_INTERNAL = 0x2d
        EXTENDED_SET_GET = 0x2e
        READ_WRITE_ALDB = 0x2f
        IMETER_RESET = 0x80
        IMETER_QUERY = 0x82

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
        raise NotImplementedError("%s.from_bytes() not implemented" % cls)

    #-----------------------------------------------------------------------
    @classmethod
    def msg_size(cls, raw):
        """Return the read message size in bytes.

        This is the input message size to read when we see msg_code in the
        byte stream.

        Standard and Extended messages depend on the message flags inside the
        message so some types will need to parse part of the byte array to
        figure out the total size.

        Args:
          raw (bytes):  The current byte stream to read from.

        Returns:
          int:  Returns the number of bytes needed to construct the message.
        """
        if cls.fixed_msg_size:
            return cls.fixed_msg_size
        else:
            raise NotImplementedError("%s.msg_size() not implemented" % cls)

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the message to a byte array.

        Returns:
          bytes:  Returns the message as bytes.
        """
        # NOTE: This is only needed for output messages.
        raise NotImplementedError("%s.to_bytes() not implemented" %
                                  self.__class__)

    #-----------------------------------------------------------------------

#===========================================================================
