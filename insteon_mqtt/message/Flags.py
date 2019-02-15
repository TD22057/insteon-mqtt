#===========================================================================
#
# Standard/extended message flag class
#
#===========================================================================
import enum


class Flags:
    """Standard and extended message flags.

    This class handles message bit flags for all many different Insteon
    message types.  It can be converted to/from bytes.
    """

    # Message types
    class Type(enum.IntEnum):
        BROADCAST = 0b100
        DIRECT = 0b000
        DIRECT_ACK = 0b001
        DIRECT_NAK = 0b101
        ALL_LINK_BROADCAST = 0b110
        ALL_LINK_CLEANUP = 0b010
        CLEANUP_ACK = 0b011
        CLEANUP_NAK = 0b111

    #-----------------------------------------------------------------------
    @classmethod
    def from_bytes(cls, raw, offset=0):
        """Read from bytes.

        The inverse of this is Flags.to_bytes().  This is used to parse the
        flags from the raw serial byte.

        Args:
          raw (bytearray):  The byte array to read from.  1 byte is required.
           offset (int):  The index in raw to read from.

        Returns:
          Returns the constructed Flags object.
        """
        b = raw[offset]

        # Mask the flags we want and then shift to get an integer.
        type = (b & 0b11100000) >> 5
        is_ext = (b & 0b00010000) >> 4
        hops_left = (b & 0b00001100) >> 2
        max_hops = (b & 0b00000011) >> 0
        return Flags(type, bool(is_ext), hops_left, max_hops)

    #-----------------------------------------------------------------------
    def __init__(self, type, is_ext, hops_left=3, max_hops=3):
        """Constructor

        Args:
          type (int):  Integer message type code.  See Flags.Type.
          is_ext (bool):  True if this is an extended message.  False if it's
                 a standard message.
          hops_left (int):  Number of message hops left.
          max_hops (int):  Maximum number of message hops.
        """
        assert hops_left >= 0 and hops_left <= 3
        assert max_hops >= 0 and max_hops <= 3

        self.type = self.Type(type)
        self.is_ext = is_ext
        self.hops_left = hops_left
        self.max_hops = max_hops
        self.is_nak = type in (Flags.Type.DIRECT_NAK, Flags.Type.CLEANUP_NAK)
        self.is_broadcast = type == Flags.Type.ALL_LINK_BROADCAST

    #-----------------------------------------------------------------------
    def set_hops(self, max_hops):
        """Set the maximum number of hops for the message.

        Args:
          max_hops (int):  Maximum number of hops to allow.  Must be in the
                   range [0,3].  Sets hops_left and max_hops to this value.
        """
        assert max_hops >= 0 and max_hops <= 3
        self.hops_left = max_hops
        self.max_hops = max_hops

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert to bytes.

        The inverse of this is Flags.from_bytes().  This is used to output
        the flags as bytes.

        Returns:
          bytes:  Returns a 1 byte array containing the bit flags.
        """
        value = self.type.value << 5 | \
                self.is_ext << 4 | \
                self.hops_left << 2 | \
                self.max_hops
        return bytes([value])

    #-----------------------------------------------------------------------
    def __eq__(self, rhs):
        """Checks if a flags object is the same as this one.

        This ignores differences in the hops_left and max_hops field.

        Args:
          rhs (Flags):  The object to compare to this one

        Returns:
          bool:  True if the objects are the same.
        """
        return (isinstance(rhs, Flags) and
                self.type == rhs.type and
                self.is_ext == rhs.is_ext)

    #-----------------------------------------------------------------------
    def __str__(self):
        return "%s%s" % (self.type, '' if not self.is_ext else ' ext')

    #-----------------------------------------------------------------------
