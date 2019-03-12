#===========================================================================
#
# Insteon Address class
#
#===========================================================================


class Address:
    """Insteon address class.

    This class stores an Insteon 3 byte device address.  It can be
    constructed from a variety of inputs (see the constructor) and supports
    conversion to/from bytes (for I/O) and json (for configuration files).

    Once constructed, the address has the following attributes:
    - id    (int) The integer ID of the address.
    - ids   ([int]) List of the three byte ID's of the address.
    - hex   (str) A nicely formatted hex string of the address.

    The Address class supports hash and comparisons so it can be used as a
    dictionary key.
    """
    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(raw, offset=0):
        """Read an Address from a list of bytes.

        The inverse of this is to_bytes().

        Args:
          raw (bytes):  The bytearray or list of bytes to read from.
          offset (int):  The offset in raw to start reading at.

        Returns:
          Address: Returns the created Address object.
        """
        return Address(raw[0 + offset], raw[1 + offset], raw[2 + offset])

    #-----------------------------------------------------------------------
    @staticmethod
    def from_json(data):
        """Read an Address from a JSON input.

        The inverse of this is to_json().

        Args:
          data (str):  The address string to read from.  For valid strings,
               see the constructor docs.

        Returns:
          Address: Returns the created Address object.
        """
        return Address(data)

    #-----------------------------------------------------------------------
    def __init__(self, addr, addr2=None, addr3=None):
        """Construct an Address object.

        An address has three bytes AA, BB, and CC that need to be input.  The
        address can be input as a single field or as three fields.  Valid
        single field inputs are:

        - String containing the hex address in upper or lower case.  Valid
          inputs have the form 'AABBCC', 'AA.BB.CC', 'AA:BB:CC', or
          'AA BB CC'
        - Integer address (6 byte integer)
        - An existing Address object to copy.

        Valid three field inputs are:

        - Strings with a single hex byte input in each.  Valid forms are 'A0'
          or '0xA0'
        - Integers in the range 0 -> 255.

        Args:
          addr:   Insteon address input.
          addr2:  Optional 2nd address input.
          addr3:  Optional 3rd address input.
        """
        # Error if: no address is input, or not both addr2 and addr3 are
        # input.
        if (addr is None or
                (addr is not None and addr2 is not None and addr3 is None) or
                (addr is not None and addr2 is None and addr3 is not None)):
            msg = ("Error trying to parse an Insteon address.  The input "
                   "can be a single integer, string, or 3 bytes or "
                   "strings.  Inputs: %s, %s, %s" % (addr, addr2, addr3))
            raise Exception(msg)

        # First input has all 3 byte values.
        if addr2 is None:
            id1, id2, id3 = self._addr1_to_ids(addr)

        # Input is split into 3 parts
        else:
            id1, id2, id3 = self._addr3_to_ids(addr, addr2, addr3)

        # Store the 3 integer address ID's
        self.ids = [id1, id2, id3]

        # Convert the 3 integer values to a single integer ID to use.
        self.id = (id1 << 16) | (id2 << 8) | id3

        # Create the byte sequence for the address.
        self.bytes = bytes(self.ids)

        # And a nicely formatted hex string output.
        self.hex = ("%02X.%02X.%02X" % tuple(self.ids)).lower()

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Write an Address to a list of bytes.

        The inverse of this is from_bytes().

        Returns:
          bytes: Returns the the three byte address as a bytes.
        """
        return self.bytes

    #-----------------------------------------------------------------------
    def to_json(self):
        """Write an Address to JSON format.

        The inverse of this is from_json().

        Returns:
          str: Returns the address as a hex string.
        """
        return self.hex

    #-----------------------------------------------------------------------
    def __hash__(self):
        return self.id.__hash__()

    #-----------------------------------------------------------------------
    def __eq__(self, rhs):
        return isinstance(rhs, Address) and self.id == rhs.id

    #-----------------------------------------------------------------------
    def __lt__(self, rhs):
        return self.id < rhs.id

    #-----------------------------------------------------------------------
    def __str__(self):
        return self.hex

    #-----------------------------------------------------------------------
    def _addr1_to_ids(self, addr):
        """Convert a single input to an Address

        Arg:
          addr:  Single string or integer address specification.

        Returns:
          [int]: Returns a list of the three integer ID fields.
        """
        # Copy construction.
        if isinstance(addr, Address):
            return addr.ids

        # Convert from a string to an integer ID.
        elif isinstance(addr, str):
            # Handles 'AABBCC' 'AA.BB.CC' 'AA:BB:CC' 'AA BB CC'
            s = addr.replace(".", "").replace(":", "").replace(" ", "").strip()
            id = int(s, 16)

        # Single integer input.
        elif isinstance(addr, int):
            id = addr

        else:
            msg = ("Error trying to parse an Insteon address.  The input "
                   "address must be an integer or string: %s" % addr)
            raise Exception(msg)

        if id < 0 or id > 0xFFFFFF:
            msg = ("Error trying to parse an Insteon address.  The input "
                   "address must in the range 0 >= %s <= %s:  Input: "
                   % (id, 0xFFFFFF))
            raise Exception(msg)

        # Convert the single integer to 3 individual bytes.
        id1 = id >> 16 & 0xFF
        id2 = id >> 8 & 0xFF
        id3 = id & 0xFF
        return (id1, id2, id3)

    #-----------------------------------------------------------------------
    def _addr3_to_ids(self, a1, a2, a3):
        """Convert three inputs to an Address

        Arg:
          a1:  First address input.
          a2:  Second address input.
          a3:  Third address input.

        Returns:
          [int]: Returns a list of the three integer ID fields.
        """
        # Convert from an string in base 16 or directly to an integer.
        id1 = int(a1) if not isinstance(a1, str) else int(a1, 16)
        id2 = int(a2) if not isinstance(a2, str) else int(a2, 16)
        id3 = int(a3) if not isinstance(a3, str) else int(a3, 16)

        if id1 > 255 or id2 > 255 or id3 > 255:
            msg = ("Error trying to parse an Insteon a1ess.  The input "
                   "integer values must be in the range 0->255 (0x00-"
                   "0xFF).  Inputs: %s, %s, %s" % (a1, a2, a3))
            raise Exception(msg)

        return (id1, id2, id3)

    #-----------------------------------------------------------------------
