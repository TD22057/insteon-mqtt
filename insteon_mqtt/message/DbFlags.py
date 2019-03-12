#===========================================================================
#
# Database message bit flags
#
#===========================================================================
from .. import util


class DbFlags:
    """All link database record control bit flags.

    This class handles message bit flags for all link database records.  It
    can be converted to/from bytes and to/from JSON format.
    """
    #-----------------------------------------------------------------------
    @classmethod
    def from_json(cls, data):
        """Read from JSON data.

        The inverse of this is DbFlags.to_json().  This is used when saving
        and loading the record flags from a JSON file.

        Args:
          data (dict):  JSON data to read from.

        Returns:
          Returns the constructed DbFlags object.
        """
        return DbFlags(data['in_use'], data['is_controller'],
                       data['is_last_rec'])

    #-----------------------------------------------------------------------
    @classmethod
    def from_bytes(cls, raw, offset=0):
        """Read from bytes.

        The inverse of this is DbFlags.to_bytes().  This is used to parse the
        flags from the raw serial byte.

        Args:
          raw (bytearray):  The byte array to read from.  1 byte is required.
          offset (int):  The index in raw to read from.

        Returns:
          Returns the constructed DbFlags object.
        """
        # pylint: disable=superfluous-parens
        b = raw[offset]

        # Extract the bit flags we need for the record.
        in_use = (b & 0b10000000) >> 7
        is_controller = (b & 0b01000000) >> 6
        # bits 2-5 are unused

        # high water bit: 0 for last record, 1 otherwise
        is_last_rec = not ((b & 0b00000010) >> 1)
        # bit 0 is not needed

        return DbFlags(bool(in_use), bool(is_controller), is_last_rec)

    #-----------------------------------------------------------------------
    def __init__(self, in_use, is_controller, is_last_rec):
        """Constructor

        Args:
          in_use (bool):  True if the record is in use.
          is_controller (bool):  True means the device holding the record is
                        the controller.  False means it's a responder.
          is_last_rec (bool):  True if this is the last record in the database.
        """
        self.in_use = in_use
        self.is_controller = is_controller
        self.is_last_rec = is_last_rec

    #-----------------------------------------------------------------------
    def copy(self):
        """Make a copy of the object.

        Returns:
          Returns a new DbFlags object.
        """
        return DbFlags(self.in_use, self.is_controller, self.is_last_rec)

    #-----------------------------------------------------------------------
    def to_bytes(self, modem_delete=False):
        """Convert to bytes.

        The inverse of this is DbFlags.from_bytes().  This is used to output
        the flags as bytes.

        Args:
          is_delete (bool):  Set to True if this is delete call to the modem
                    to modify the database.

        Returns:
           bytes:  Returns a 1 byte array containing the bit flags.
        """
        data = self.in_use << 7
        data |= self.is_controller << 6
        data |= (not self.is_last_rec) << 1

        # Not sure why this is needed.  Insteon docs say bit 5 is unused.
        # But all the records have it set and if it's not set here, commands
        # sent to modify the database will fail.  But, for delete calls to
        # the modem db, this must be zero.
        if not modem_delete:
            data |= 1 << 5

        return bytes([data])

    #-----------------------------------------------------------------------
    def to_json(self):
        """Write to JSON data.

        The inverse of this is DbFlags.from_json().  This is used when saving
        and loading the record flags from a JSON file.

        Returns:
          dict:  Returns a dictionary of the JSON data for the class.
        """
        return {
            'in_use' : self.in_use,
            'is_controller' : self.is_controller,
            'is_last_rec' : self.is_last_rec,
            }

    #-----------------------------------------------------------------------
    def __str__(self):
        return ("in_use: %s type: %s last: %s" %
                (self.in_use, util.ctrl_str(self.is_controller),
                 self.is_last_rec))

    #-----------------------------------------------------------------------
