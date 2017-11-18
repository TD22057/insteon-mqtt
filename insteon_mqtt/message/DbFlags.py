#===========================================================================
#
# Database message bit flags
#
#===========================================================================


#===========================================================================

class DbFlags:
    """All link database record control bit flags.

    This class handles message bit flags for all link database
    records.  It can be converted to/from bytes and to/from JSON
    format.
    """
    #-----------------------------------------------------------------------
    @staticmethod
    def from_json(data):
        """Read from JSON data.

        The inverse of this is DbFlags.to_json().  This is used when
        saving and loading the record flags from a JSON file.

        Args:
           data:  (dict) JSON data to read from.

        Returns:
           Returns the constructed DbFlags object.
        """
        return DbFlags(data['in_use'], data['is_controller'],
                       data['high_water'])

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

        # Extract the bit flags we need for the record.
        in_use = (b & 0b10000000) >> 7
        is_controller = (b & 0b01000000) >> 6
        # bits 2-5 are unused
        high_water = (b & 0b00000010) >> 1
        # bit 0 is not needed

        return DbFlags(bool(in_use), bool(is_controller), bool(high_water))

    #-----------------------------------------------------------------------
    def __init__(self, in_use, is_controller, high_water):
        """Constructor

        Args:
          in_use:         (bool) True if the record is in use.
          is_controller:  (bool) True if the record is for a controller,
                          False for a responder.
          high_water:     (bool) True if this is the last valid record in use.
        """
        self.in_use = in_use
        self.is_controller = is_controller
        self.is_responder = not is_controller
        self.high_water = high_water

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert to bytes.

        The inverse of this is DbFlags.from_bytes().  This is used to
        output the flags as bytes.

        Returns:
           (bytes) Returns a 1 byte array containing the bit flags.
        """
        data = self.in_use << 7 | \
               self.is_controller << 6 | \
               self.high_water << 1
        return bytes([data])

    #-----------------------------------------------------------------------
    def to_json(self):
        """Write to JSON data.

        The inverse of this is DbFlags.from_json().  This is used when
        saving and loading the record flags from a JSON file.

        Returns:
           (dict) Returns a dictionary of the JSON data for the class.
        """
        return {
            'in_use' : self.in_use,
            'is_controller' : self.is_controller,
            'high_water' : self.high_water,
            }

    #-----------------------------------------------------------------------
    def __str__(self):
        return "in_use: %s type: %s used: %s" % \
            (self.in_use, 'CTRL' if self.is_controller else 'RESP',
             self.high_water)

    #-----------------------------------------------------------------------
