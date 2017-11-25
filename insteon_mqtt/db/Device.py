#===========================================================================
#
# Non-modem device all link database class
#
#===========================================================================
import io
import logging
from ..Address import Address
from .. import handler
from .. import message as Msg
from .DeviceEntry import DeviceEntry

LOG = logging.getLogger(__name__)


class Device:
    """Device all link database.

    This class stores the all link database for an Insteon device.
    Each item is a DeviceEntry object that contains a single remote
    address, group, and type (controller vs responder).

    The database can be read to and written from JSOn format.
    Normally the db is constructed via message.InpExtended objects
    being read and parsed after requesting them from the device.
    """
    @staticmethod
    def from_json(data):
        """Read a Device database from a JSON input.

        The inverse of this is to_json().

        Args:
          data:    (dict): The data to read from.

        Returns:
          Device: Returns the created Device object.
        """
        obj = Device(Address(data['address']))

        obj.delta = data['delta']

        for d in data['used']:
            entry = DeviceEntry.from_json(d)
            obj._add_used(entry)

        for d in data['unused']:
            entry = DeviceEntry.from_json(d)
            obj._add_unused(entry)

        return obj

    #-----------------------------------------------------------------------
    def __init__(self, addr):
        """Constructor
        """
        self.addr = addr

        # All link delta number.  This is incremented by the device
        # when the db changes on the device.  It's returned in a
        # refresh (cmd=0x19) call to the device so we can check it
        # against the version we have stored.
        self.delta = None

        # List of DeviceEntry objects.  One per entry in the database.
        self.entries = []

        # List of DeviceEntry objects that are on the device but
        # unused.  We need to keep these so we can use these storage
        # locations for future entries.
        self.unused = []

        # Map of all link group number to DeviceEntry objects that
        # respond to that group command.
        self.groups = {}

        # Set of memory addresses that we have entries for.  This is
        # cleared when we start to download the db and used to filter
        # out duplicate entries.  Some devcies (smoke bridge) report a
        # lot of duplicate entries for some reason.
        self._mem_locs = set()

    #-----------------------------------------------------------------------
    def is_current(self, delta):
        """See if the database is current.

        The current delta is reported in the device status messages.
        Compare that against the stored delta in the database to see
        if this database is current.  If it's not, a new database
        needs to be downloaded from the device.

        Args:
          delta:  (int) The database delta to check

        Returns:
          (bool) Returns True if the database delta matches the input.
        """
        return delta == self.delta

    #-----------------------------------------------------------------------
    def clear_delta(self):
        """Clear the current database device delta.

        This will cause any future is_current() check to fail in order
        to force a database download.
        """
        self.delta = None

    #-----------------------------------------------------------------------
    def clear(self):
        """Clear the complete database of entries.
        """
        self.delta = None
        self.entries.clear()
        self.unused.clear()
        self.groups.clear()
        self._mem_locs.clear()

    #-----------------------------------------------------------------------
    def __len__(self):
        return len(self.entries)

    #-----------------------------------------------------------------------
    def delete_entry(self, protocol, device_addr, entry):
        """TODO: doc
        """
        # see p117 of insteon dev guide: To delete a record, set the
        # in use flag in DbFlags to 0.

        # Copy the DbFlags and mark it as unused.
        db_flags = Msg.DbFlags.from_bytes(entry.db_flags.to_bytes())
        db_flags.in_use = False
        #db_flags.is_controller = not db_flags.is_controller  # TODO??

        # If this is the last record in the database, set it's last
        # record flag to 1.
        if entry == self.entries[-1]:
            db_flags.is_last_rec = True

        # Build the extended db modification message.  This says to
        # modify the entry in place w/ the new db flags.
        ext_data = entry.to_bytes(db_flags)
        msg = Msg.OutExtended.direct(device_addr, 0x2f, 0x00, ext_data)

        msg_handler = handler.DeviceModifyDb(self, self._handle_delete,
                                             entry=entry)

        # Send the message.
        protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def _handle_delete(self, msg, entry):
        """TODO: doc
        """
        assert isinstance(msg, Msg.InpStandard)

        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.info("Device.delete removed entry: %s", entry)
            self.entries.remove(entry)
            self._mem_locs.remove(entry.mem_loc)
            # TODO: self.save()

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("Device.delete NAK removing entry: %s", entry)
        else:
            LOG.error("Device.delete unexpected msg type: %s", msg)

    #-----------------------------------------------------------------------
    def handle_db_rec(self, msg):
        """Handle a InpExtended database record message.

        This parses the input message into a DeviceEntry record and
        adds it to the database.

        Args:
          msg:  (InpExtended) The database record to parse.

        Returns:
        TODO: doc
        """
        assert isinstance(msg, Msg.InpExtended)
        assert msg.data[1] == 0x01  # record response

        entry = DeviceEntry.from_bytes(msg.data)
        if entry.mem_loc in self._mem_locs:
            LOG.info("Skipping duplicate entry %s grp: %s lev: %s", entry.addr,
                     entry.group, entry.on_level)
            return Msg.CONTINUE

        # Entry is valid, store it in the database.
        if entry.db_flags.in_use:
            LOG.info("Adding db record %s grp: %s lev: %s", entry.addr,
                     entry.group, entry.on_level)
            self._add_used(entry)

        # If the entry is marked as not in use, store it as unused so
        # we can use the memory location for future additions to the
        # database.
        else:
            LOG.info("Ignoring device db record in_use = False")
            self._add_unused(entry)

        if entry.db_flags.is_last_rec:
            return Msg.FINISHED
        else:
            return Msg.CONTINUE

    #-----------------------------------------------------------------------
    def find_group(self, group):
        """Find the database entries in a group.

        Args:
          group:  (int) The group ID to find.

        Returns:
          [DeviceEntry] Returns a list of the database device entries that
          match the input group ID.
        """
        entries = self.groups.get(group, [])
        return entries

    #-----------------------------------------------------------------------
    def find(self, addr, group, is_controller):
        """Find a database record by address, group, and record type.

        Args:
          addr:   (Address) The device address.
          group:  (int) The group ID.
          TODO: doc type:   ('RESP' or 'CTRL') Responder or controller
                     record type.
        Returns:
          (DeviceEntry) Returns the database DeviceEntry if found or None
          if the entry doesn't exist.
        """
        for e in self.entries:
            if (e.addr == addr and e.group == group and
                    e.is_controller == is_controller):
                return e

        return None

    #-----------------------------------------------------------------------
    def to_json(self):
        """Convert the database to JSON format.

        Returns:
          (dict) Returns the database as a JSON dictionary.
        """
        used = [i.to_json() for i in self.entries]
        unused = [i.to_json() for i in self.unused]
        return {
            'address' : self.addr.to_json(),
            'delta' : self.delta,
            'used' : used,
            'unused' : unused,
            }

    #-----------------------------------------------------------------------
    def __str__(self):
        o = io.StringIO()
        o.write("DeviceDb: (delta %s)\n" % self.delta)
        for elem in sorted(self.entries, key=lambda i: i.addr.id):
            o.write("  %s\n" % elem)

        o.write("GroupMap\n")
        for grp, elem in self.groups.items():
            o.write("  %s -> %s\n" % (grp, [i.addr.hex for i in elem]))

        return o.getvalue()

    #-----------------------------------------------------------------------
    def _add_used(self, entry):
        """Add an in use DeviceEntry

        Args:
          entry:  (DeviceEntry) The entry to add.
        """
        self.entries.append(entry)
        self._mem_locs.add(entry.mem_loc)

        # If we're the controller for this entry, add it to the list
        # of entries for that group.
        if entry.db_flags.is_controller:
            responders = self.groups.setdefault(entry.group, [])
            if entry not in responders:
                responders.append(entry)

    #-----------------------------------------------------------------------
    def _add_unused(self, entry):
        """Add a not in use DeviceEntry

        Args:
          entry:  (DeviceEntry) The entry to add.
        """
        self.unused.append(entry)
        self._mem_locs.add(entry.mem_loc)

    #-----------------------------------------------------------------------
