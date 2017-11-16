#===========================================================================
#
# Standard/extended message flag class
#
#===========================================================================
import io

#===========================================================================

class Flags:
    """Standard and extended message flags.

    This class handles message bit flags for all many different
    Insteon message types.  It can be converted to/from bytes.
    """

    # Message types
    BROADCAST = 0b100
    DIRECT = 0b000
    DIRECT_ACK = 0b001
    DIRECT_NAK = 0b101
    ALL_LINK_BROADCAST = 0b110
    ALL_LINK_CLEANUP = 0b010
    CLEANUP_ACK = 0b011
    CLEANUP_NAK = 0b111

    # Map of message type bit flags to labels.
    label = {
        BROADCAST : 'BROADCAST',
        DIRECT : 'DIRECT',
        DIRECT_ACK : 'DIRECT_ACK',
        DIRECT_NAK : 'DIRECT_NAK',
        ALL_LINK_BROADCAST : 'ALL_LINK_BROADCAST',
        ALL_LINK_CLEANUP : 'ALL_LINK_CLEANUP',
        CLEANUP_ACK : 'CLEANUP_ACK',
        CLEANUP_NAK : 'CLEANUP_NAK',
        }

    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(raw, offset=0):
        """Read from bytes.

        The inverse of this is DbFlags.to_bytes().  This is used to
        parse the flags from the raw serial byte.

        Args:
           raw:    (bytearray) The byte array to read from.  1 byte
                   is required.
           offset: (int)The index in raw to read from.

        Returns:
           Returns the constructed DbFlags object.
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
          type:       Integer message type code.
          is_ext:     (bool) True if this is an extended message.  False if
                      it's a standard message.
          hops_left:  (int) Number of message hops left.
          max_hops:   (int) Maximum number of message hops.
        """
        assert type >= 0 and type <= 0b111
        assert hops_left >= 0 and hops_left <= 3
        assert max_hops >= 0 and max_hops <= 3

        self.type = type
        self.is_ext = is_ext
        self.hops_left = hops_left
        self.max_hops = max_hops
        self.is_nak = type == Flags.DIRECT_NAK or type == Flags.CLEANUP_NAK
        self.is_broadcast = type == Flags.ALL_LINK_BROADCAST

        self.byte = self.type << 5 | \
                    self.is_ext << 4 | \
                    self.hops_left << 2 | \
                    self.max_hops

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert to bytes.

        The inverse of this is Flags.from_bytes().  This is used to
        output the flags as bytes.

        Returns:
           (bytes) Returns a 1 byte array containing the bit flags.
        """
        return bytes([self.byte])

    #-----------------------------------------------------------------------
    def __str__(self):
        o = io.StringIO()
        o.write("%s%s" % (Flags.label[self.type],
                          '' if not self.is_ext else ' ext'))
        return o.getvalue()

    #-----------------------------------------------------------------------
