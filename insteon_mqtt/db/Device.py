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
            obj._add_used(entry)  # pylint: disable=protected-access

        for d in data['unused']:
            entry = DeviceEntry.from_json(d)
            obj._add_unused(entry)  # pylint: disable=protected-access

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

        # Map of memory address (int) to DeviceEntry objects.
        self.entries = {}

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
        # lot of duplicate entries during db download for some reason.
        self._mem_locs = set()

        # TODO: handle case where we send modify and get another
        # modify request before the original is done.  Need to track
        # memory locs.  Same w/ delete - need to wait until we know
        # how the first one finished before we queue up the next one.

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
    def add_entry(self, protocol, device_addr, addr, group, data,
                  is_controller):
        # If the record already exists, don't do anything.
        if self.find(addr, group, is_controller):
            # TODO: support checking and updating data
            LOG.warning("Device %s add db already exists for %s grp %s %s",
                        device_addr, addr, group,
                        'CTRL' if is_controller else 'RESP')
            return

        LOG.info("Device %s adding db: %s grp %s %s %s", device_addr, addr,
                 group, 'CTRL' if is_controller else 'RESP', data)
        assert len(self.entries)

        # If there are entries in the db that are mark unused, we can
        # re-use those memory addresses and just update them w/ the
        # correct information and mark them as used.
        if self.unused:
            # Grab the first unused entry.
            entry = self.unused.pop(0)
            LOG.info("Device %s using unused entry at mem %#06x",
                     device_addr, entry.mem_loc)

            # Update it w/ the new information.
            entry.update_from(addr, group, is_controller, data)

            # Build the extended db modification message.  This says to
            # update the record at the entry memory location.
            ext_data = entry.to_bytes()
            msg = Msg.OutExtended.direct(device_addr, 0x2f, 0x00, ext_data)
            msg_handler = handler.DeviceDbAdd(self, entry)

        # If there no unused entries, we need to append one.  Write a
        # new record at the next memory location below the current
        # last entry and mark that as the new last entry.  If that
        # works, then update the record before it (the old last entry)
        # and mark it as not being the last entry anymore.  This order
        # is important since if either operation fails, the db is
        # still in a valid order.
        else:
            # Memory goes high->low so find the last entry by looking
            # at the minimum value.  Then find the entry for that loc.
            last_entry = self.find_mem_loc(min(self._mem_locs))

            # Each rec is 8 bytes so move down 8 to get the next loc.
            mem_loc = last_entry.mem_loc - 0x08
            LOG.info("Device %s appending new record at mem %#06x",
                     device_addr, mem_loc)

            # Create the new entry and send it out.
            db_flags = Msg.DbFlags(in_use=True, is_controller=is_controller,
                                   is_last_rec=True)
            entry = DeviceEntry(addr, group, mem_loc, db_flags, data)
            ext_data = entry.to_bytes()
            msg = Msg.OutExtended.direct(device_addr, 0x2f, 0x00, ext_data)
            msg_handler = handler.DeviceDbAdd(self, entry)

            # Now create the updated current last entry w/ the last
            # record flag set to False since it's not longer last.
            # The handler will send this message out if the first call
            # above gets an ACK.
            new_last = last_entry.copy()
            new_last.db_flags.is_last_rec = False
            ext_data = new_last.to_bytes()
            next_msg = Msg.OutExtended.direct(device_addr, 0x2f, 0x00, ext_data)
            msg_handler.add_update(next_msg, new_last)

        # Send the message and handler.
        protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def delete_entry(self, protocol, device_addr, entry):
        """TODO: doc
        """
        # see p117 of insteon dev guide: To delete a record, set the
        # in use flag in DbFlags to 0.

        # Copy the entry and mark it as unused.
        new_entry = entry.copy()
        new_entry.db_flags.in_use = False

        # TODO: clean this up.  keep old?  pass both to handler?  or
        # what?  have handler erase old and push new?

        # Build the extended db modification message.  This says to
        # modify the entry in place w/ the new db flags which say this
        # record is no longer in use.
        ext_data = new_entry.to_bytes()
        msg = Msg.OutExtended.direct(device_addr, 0x2f, 0x00, ext_data)
        # TODO: clean this up
        #msg_handler = handler.DeviceDbDelete(self, self._handle_delete,
        #                                     entry=new_entry)
        msg_handler = handler.DeviceDbAdd(self, new_entry)

        # Send the message.
        protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_entry(self, entry):
        """TODO: doc
        """
        # Entry could be new or an update to an existing entry.
        if entry.db_flags.in_use:
            LOG.info("Updating entry: %s", entry)
            self._add_used(entry)
        else:
            # TODO: ?? can this ever happen?  SHoul donly happen on delete.
            LOG.info("Removing entry: %s", entry)
            if not self.entries.pop(entry.mem_loc, None):
                LOG.error("TODO: entry didn't exit: %s\n5s", entry, self)

            self._add_unused(entry)

        # TODO: save db locally
        LOG.error(self)

    #-----------------------------------------------------------------------
    def _handle_delete(self, msg, entry):
        """TODO: doc
        """
        assert isinstance(msg, Msg.InpStandard)

        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.info("Device.delete removed entry: %s", entry)

            # Remove the original entry from the in use list.  The new
            # entry with the correct flags is passed to us.  Set that
            # into the unused list.
            del self.entries[entry.mem_loc]
            self.unused.append(entry)

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
                     entry.group, entry.data[0])
            return Msg.CONTINUE

        # Entry is valid, store it in the database.
        if entry.db_flags.in_use:
            LOG.info("Adding db record %s grp: %s lev: %s", entry.addr,
                     entry.group, entry.data[0])
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
        for e in self.entries.values():
            if (e.addr == addr and e.group == group and
                    e.is_controller == is_controller):
                return e

        return None

    #-----------------------------------------------------------------------
    def find_mem_loc(self, mem_loc):
        """TODO: doc
        """
        return self.entries.get(mem_loc, None)

    #-----------------------------------------------------------------------
    def find_all(self, addr=None, group=None, is_controller=None):
        """TODO: doc
        """
        results = []

        for e in self.entries.values():
            if addr is not None and e.addr != addr:
                continue
            if group is not None and e.group != group:
                continue
            if is_controller is not None and e.is_controller != is_controller:
                continue

            results.append(e)

        return results

    #-----------------------------------------------------------------------
    def to_json(self):
        """Convert the database to JSON format.

        Returns:
          (dict) Returns the database as a JSON dictionary.
        """
        used = [i.to_json() for i in self.entries.values()]
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
        #TODO: for elem in sorted(self.entries.values(), key=lambda i: i.addr.id):
        for elem in sorted(self.entries.values(), key=lambda i: i.mem_loc):
            o.write("  %s\n" % elem)

        o.write("Unused:\n")
        for elem in sorted(self.unused, key=lambda i: i.mem_loc):
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
        # NOTE: this relies on no-one keeping a handle to this
        # entry outside of this class.
        self.entries[entry.mem_loc] = entry
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

        # If the entry is a controller and it's in the group dict,
        # erase it from the group map.
        if entry.db_flags.is_controller and entry.group in self.groups:
            responders = self.groups[entry.group]
            for i in range(len(responders)):
                if responders[i].addr == entry.addr:
                    del responders[i]
                    break

    #-----------------------------------------------------------------------
