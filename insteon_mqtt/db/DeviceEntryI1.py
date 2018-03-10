#===========================================================================
#
# Non-modem device all link database class for i1 devices
#
#===========================================================================
import io
from .DeviceEntry import DeviceEntry
from ..Address import Address
from .. import log
from .. import message as Msg


LOG = log.get_logger()


#===========================================================================
class DeviceEntryI1(DeviceEntry):
    """Device all link database entry for i1 devices.

    Inherits almost everything from DeviceEntry with exception of from_bytes
    and to_bytes.
    """

    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(data):
        """Read a DeviceEntryI1 from a byte array.

        This is used to read an entry from the DeviceScanManagerI1 handler for
        i1 devices.  The manager caches all of the bytes until it has an
        entire record and then passes it here.

        Args:
          data:      (bytes) The 8 byte record, preceeded by the 2 byte
                     location.

        Returns:
          DeviceEntryI1: Returns the created DeviceEntry object.
        """

        mem_loc = (data[0] << 8) + data[1]
        db_flags = Msg.DbFlags.from_bytes(data, 2)
        group = data[3]
        link_addr = Address.from_bytes(data, 4)
        link_data = data[7:10]

        return DeviceEntry(link_addr, group, mem_loc, db_flags, link_data)

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the entry to a 8 byte byte array.

        Returns:
          (bytes) Returns the 8 byte data array.
        """
        o = io.BytesIO()
        o.write(self.db_flags.to_bytes())
        o.write(bytes([self.group]))
        o.write(self.addr.to_bytes())
        o.write(self.data)

        data = o.getvalue()
        assert len(data) == 8
        return data
