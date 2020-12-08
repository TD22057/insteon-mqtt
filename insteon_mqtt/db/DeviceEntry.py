#===========================================================================
#
# Non-modem device all link database class
#
#===========================================================================
import io
from ..Address import Address
from .. import log
from .. import message as Msg
from .. import util

LOG = log.get_logger()


#===========================================================================
class DeviceEntry:
    """Device all link database entry.

    Each entry in the device's all link database has the address of the
    remote device, the group the device is part of, and various flags for the
    entry.

    The entry can be converted to/from JSON with to_json() and from_json().

    Notes on the values for Data 1-3 in links:
      Responder Records
        Data 1    Link-specific data (e.g. On-Level)
        Data 2    Link-specific data (e.g. Ramp Rates, Setpoints, etc.)
        Data 3    Link-specific data (listed by Insteon as "normally unused"
                             but for multi-function items, we know that this
                             is set to the linked "group" on the responding
                             device)

      Controller Records
        Data 1    Number of retries (Normally set to 03, FF = no retries,
                  00 = Broadcast for cleanup)
        Data 2    Listed as Ignored?
        Data 3    Listed as 00 for switchlinc type devices and 01-08 for KPL
                  type devices
    """

    @staticmethod
    def from_json(data, db=None):
        """Read a DeviceEntry from a JSON input.

        The inverse of this is to_json().

        Args:
          data:    (dict): The data to read from.

        Returns:
          DeviceEntry: Returns the created DeviceEntry object.
          db: (db.Device) The parent database which contains this entry
        """
        return DeviceEntry(Address.from_json(data['addr']),
                           data['group'],
                           data['mem_loc'],
                           Msg.DbFlags.from_json(data['db_flags']),
                           bytes(data['data']),
                           db=db)

    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(data, db=None):
        """Read a DeviceEntry from a byte array.

        This is used to read an entry from an InpExtended insteon message
        object.  See p162 of the Insteon dev guide for the byte array layout.

        Args:
          data:  (bytes) The data 14 byte array from an InpExtended message.
          db:    (db.device) The parent database containing this entry

        Returns:
          DeviceEntry: Returns the created DeviceEntry object.
        """
        # See p162 and p116 of insteon dev guide
        # [0] = unused
        # [1] = request/response flag
        mem_loc = (data[2] << 8) + data[3]
        # [4] = dump request flag
        db_flags = Msg.DbFlags.from_bytes(data, 5)
        group = data[6]
        link_addr = Address.from_bytes(data, 7)
        link_data = data[10:13]

        return DeviceEntry(link_addr, group, mem_loc, db_flags,
                           link_data, db=db)

    #-----------------------------------------------------------------------
    @staticmethod
    def from_i1_bytes(data, db=None):
        """Read a DeviceEntry from an i1 device byte array.

        This is used to read an entry from the DeviceScanManagerI1 handler for
        i1 devices.  The manager caches all of the bytes until it has an
        entire record and then passes it here.

        Args:
          data:      (bytes) The 8 byte record, preceeded by the 2 byte
                     location.
          db:        (db.device) The parent database containing this entry

        Returns:
          DeviceEntry: Returns the created DeviceEntry object.
        """
        mem_loc = (data[0] << 8) + data[1]
        db_flags = Msg.DbFlags.from_bytes(data, 2)
        group = data[3]
        link_addr = Address.from_bytes(data, 4)
        link_data = data[7:10]

        return DeviceEntry(link_addr, group, mem_loc, db_flags,
                           link_data, db=db)

    #-----------------------------------------------------------------------
    def __init__(self, addr, group, mem_loc, db_flags, data, db=None):
        """Constructor

        Args:
          addr:     (Address) The address of the device in the database.
          group:    (int) The group the entry is for.
          mem_loc:  (int) The memory address location of the record.
          db_flags: (message.DbFlags) The db controler record flags.
          data:     (bytes) 3 data bytes.  [0] is the on level, [1] is the
                    ramp rate.
          db:       (db.device) The parent database containing this entry
        """
        # Accept either bytes, list of ints, or None for the data input.
        if data is not None:
            data = bytes(data)
            assert len(data) == 3
        else:
            data = bytes(3)

        self.addr = addr
        self.group = group
        self.mem_loc = mem_loc
        self.db_flags = db_flags
        self.is_controller = db_flags.is_controller
        self.data = data
        self.db = db

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
            device = self.db.device.modem.find(self.addr)
            if device is not None:
                return device.label
        return str(self.addr)

    #-----------------------------------------------------------------------
    def copy(self):
        """Make a copy of the DeviceEntry.

        Returns:
           Returns a copy of the DeviceEntry object.
        """
        return DeviceEntry(self.addr, self.group, self.mem_loc,
                           self.db_flags.copy(), self.data[:], db=self.db)

    #-----------------------------------------------------------------------
    def update_from(self, addr, group, is_controller, data):
        """Update the entry from a set of data.

        This modifies the entry using the input values.  The DblFlags.in_use
        attribute will be set to True.  This is used when an unused record is
        turned into an active record.  We update the values but leave the
        memory location alone and mark the record as now in use.

        Args:
          addr:          (Address) The address of the device in the database.
          group:         (int) The group the entry is for.
          is_controller: (bool) True if the device is a controller.
          data:          (bytes) 3 data bytes.  [0] is the on level, [1] is the
                         ramp rate.
        """
        self.addr = addr
        self.group = group
        self.db_flags.in_use = True
        self.db_flags.is_controller = is_controller
        self.is_controller = is_controller
        self.data = data

    #-----------------------------------------------------------------------
    def mem_bytes(self):
        """Return the memory location as a byte array.

        Returns:
          (bytes) Returns the record memory location as a 2 byte array.
        """
        high = (self.mem_loc & 0xFF00) >> 8
        low = (self.mem_loc & 0x00FF) >> 0
        return bytes([high, low])

    #-----------------------------------------------------------------------
    def to_json(self):
        """Convert the entry to JSON format.

        Returns:
          (dict) Returns the entry as a JSON dictionary.
        """
        return {
            'addr' : self.addr.to_json(),
            'group' : self.group,
            'mem_loc' : self.mem_loc,
            'db_flags' : self.db_flags.to_json(),
            'data' : list(self.data)
            }

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the entry to a 14 byte extended data byte array.

        Byte[1] will be set to 0x02 which is the command to update the
        remote database entry.

        Returns:
          (bytes) Returns the 14 byte data array.
        """
        # See p162 and p116 of insteon dev guide
        o = io.BytesIO()
        o.write(bytes([
            0x00,  # D1 unused
            0x02,  # D2 write record
            ]))
        o.write(self.mem_bytes())  # D3,D4 record memory location
        o.write(bytes([0x08]))  # D5 number of bytes in record
        # 8 byte record - see ALDB/L record format (page 116)
        o.write(self.db_flags.to_bytes())  # D6 db control flags
        o.write(bytes([self.group]))  # D7 group
        o.write(self.addr.to_bytes())  # D8-10 address
        o.write(self.data)  # D11-13 link data
        o.write(bytes([0x00]))  # D14 unused

        data = o.getvalue()
        assert len(data) == 14
        return data

    #-----------------------------------------------------------------------
    def to_i1_bytes(self):
        """Convert the entry to an i1 type 8 byte byte array.

        Returns:
          (bytes) Returns a 10 byte array consisting of the first two bytes
                  being the memory address and the following 8 bytes being the
                  link data.
        """
        o = io.BytesIO()
        o.write(self.mem_bytes())

        o.write(self.db_flags.to_bytes())
        o.write(bytes([self.group]))
        o.write(self.addr.to_bytes())
        o.write(self.data)

        data = o.getvalue()
        assert len(data) == 10

        return data

    #-----------------------------------------------------------------------
    def identical(self, rhs):
        """TODO: doc
        """
        return self == rhs and self.data == rhs.data

    #-----------------------------------------------------------------------
    def __eq__(self, rhs):
        """Check for equality.

        The address, group, and is_controller flags are all that are used for
        the comparison.
        """
        return (self.addr.id == rhs.addr.id and
                self.group == rhs.group and
                self.db_flags.is_controller == rhs.db_flags.is_controller)

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
        # Special tag for the last entry (memory wise) in the database.
        last = " (LAST)" if self.db_flags.is_last_rec else ""
        unused = " (UNUSED)" if not self.db_flags.in_use else ""

        return ("%04x: %-25s grp: %3s type: %s data: %#04x %#04x %#04x%s%s" %
                (self.mem_loc, self.label[:24], self.group,
                 util.ctrl_str(self.db_flags.is_controller),
                 self.data[0], self.data[1], self.data[2], unused, last))

    #-----------------------------------------------------------------------
    def __repr__(self):
        return "%04x: %s" % (self.mem_loc, self.addr.hex)

    #-----------------------------------------------------------------------
