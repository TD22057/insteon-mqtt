#===========================================================================
#
# Insteon PLM modem all link database entry
#
#===========================================================================
from ..Address import Address
from .. import log
from .. import util

LOG = log.get_logger()


class ModemEntry:
    """Modem all link database entry.

    Each entry in the modem's all link database has the address of the remote
    device, the group the device is part of, and various flags for the entry.

    The entry can be converted to/from JSON with to_json() and from_json().
    """

    @staticmethod
    def from_json(data, db=None):
        """Read a ModemEntry from a JSON input.

        The inverse of this is to_json().

        Args:
          data:    (dict): The data to read from.
          db:      (db.Modem): The Modem database which this entry belongs

        Returns:
          ModemEntry: Returns the created ModemEntry object.
        """
        return ModemEntry(Address.from_json(data['addr']),
                          data['group'],
                          data['is_controller'],
                          bytes(data['data']),
                          db=db)

    #-----------------------------------------------------------------------
    def __init__(self, addr, group, is_controller, data=None, db=None):
        """Constructor

        Args:
          addr:            (Address) The device address.
          group:           (int) The group the device is part of.
          is_controller:   (bool) True if this device is a controller of addr,
                           False if this device is a responder of addr.
          data:            (bytes) 3 data bytes.  [0] is the on level, [1]
                           is the ramp rate.
          db:              (db.Modem): The Modem database which this entry
                           belongs
        """
        # Accept either bytes, list of ints, or None for the data input.
        if data is not None:
            data = bytes(data)
            assert len(data) == 3
        else:
            data = bytes(3)

        # These should be these types but ctor them anyway to be sure.
        self.addr = Address(addr)
        self.group = int(group)
        self.is_controller = is_controller
        self.data = data
        self.db = db

    #-----------------------------------------------------------------------
    def to_json(self):
        """Convert the entry to JSON format.

        Returns:
          (dict) Returns the entry as a JSON dictionary.
        """
        return {
            'addr' : self.addr.to_json(),
            'group' : self.group,
            'is_controller' : self.is_controller,
            'data' : list(self.data)
            }

    #-----------------------------------------------------------------------
    @property
    def label(self):
        """Returns the label of the device that the address in this entry is
        associated with or the address if the device cannot be found.

        Returns:
          (str) A label or address for the entry
        """
        # We allow for no db to be set
        if self.db is not None and self.db.device is not None:
            device = self.db.device.find(self.addr)
            if device is not None:
                return device.label
        return str(self.addr)

    #-----------------------------------------------------------------------
    def __eq__(self, rhs):
        """Check for equality.

        The address, group, and is_controller flags are all that are used for
        the comparison.
        """
        return (self.addr.id == rhs.addr.id and
                self.group == rhs.group and
                self.is_controller == rhs.is_controller)

    #-----------------------------------------------------------------------
    def __lt__(self, rhs):
        """Less than.

        Uses the address and groups in the comparison.
        """
        if self.addr.id != rhs.addr.id:
            return self.addr.id < rhs.addr.id

        return self.group < rhs.group

    #-----------------------------------------------------------------------
    def __str__(self):
        return ("ID: %-25s grp: %3s type: %s  data: %#04x %#04x %#04x" %
                (self.label[:25], self.group,
                 util.ctrl_str(self.is_controller),
                 self.data[0], self.data[1], self.data[2]))

    #-----------------------------------------------------------------------
