#===========================================================================
#
# Non-modem device all link database class
#
#===========================================================================
import io
import logging
from ..Address import Address
from .. import message as Msg

LOG = logging.getLogger(__name__)


#===========================================================================
class DeviceEntry:
    """Device all link database entry.

    Each entry in the device's all link database has the address of
    the remote device, the group the device is part of, and various
    flags for the entry.

    The entry can be converted to/from JSON with to_json() and
    from_json().
    """

    @staticmethod
    def from_json(data):
        """Read a DeviceEntry from a JSON input.

        The inverse of this is to_json().

        Args:
          data:    (dict): The data to read from.

        Returns:
          DeviceEntry: Returns the created DeviceEntry object.
        """
        return DeviceEntry(Address.from_json(data['addr']),
                           data['group'],
                           data['mem_loc'],
                           Msg.DbFlags.from_json(data['db_flags']),
                           bytes(data['data']))

    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(data):
        """Read a DeviceEntry from a byte array.

        This is used to read an entry from an InpExtended insteon
        message object.  See p162 of the Insteon dev guide for the
        byte array layout.

        Args:
          data:  (bytes) The data 14 byte array from an InpExtended message.

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

        return DeviceEntry(link_addr, group, mem_loc, db_flags, link_data)

    #-----------------------------------------------------------------------
    def __init__(self, addr, group, mem_loc, db_flags, data):
        """Constructor

        Args:
          addr:     (Address) The address of the device in the database.
          group:    (int) The group the entry is for.
          mem_loc:  (int) The memory address location of the record.
          db_flags: (message.DbFlags) The db controler record flags.
          data:     (bytes) 3 data bytes.  [0] is the on level, [1] is the
                    ramp rate.
        """
        self.addr = addr
        self.group = group
        self.mem_loc = mem_loc
        self.db_flags = db_flags
        self.data = data
        self.on_level = data[0]
        self.ramp_rate = data[1]

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
        # 8 byte record (p116)
        o.write(self.db_flags.to_bytes())  # D6 db control flags
        o.write(bytes([self.group]))  # D7 group
        o.write(self.addr.to_bytes())  # D8-10 address
        o.write(self.data)  # D11-13 link data

        data = o.getvalue()
        assert len(data) == 14
        return data

    #-----------------------------------------------------------------------
    def __eq__(self, rhs):
        return (self.addr.id == rhs.addr.id and
                self.group == rhs.group and
                self.db_flags.is_controller == rhs.db_flags.is_controller)

    #-----------------------------------------------------------------------
    def __lt__(self, rhs):
        if self.addr.id != rhs.addr.id:
            return self.addr.id < rhs.addr.id

        return self.group < rhs.group

    #-----------------------------------------------------------------------
    def __str__(self):
        return "ID: %s  grp: %s  type: %s  data: %#04x %#04x %#04x" % \
            (self.addr.hex, self.group,
             'CTRL' if self.db_flags.is_controller else 'RESP',
             self.data[0], self.data[1], self.data[2])

    #-----------------------------------------------------------------------
