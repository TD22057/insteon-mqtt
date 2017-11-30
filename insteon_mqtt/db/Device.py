#===========================================================================
#
# Non-modem device all link database class
#
#===========================================================================
import functools
import io
import json
import logging
import os
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
    def from_json(data, path):
        """Read a Device database from a JSON input.

        The inverse of this is to_json().

        Args:
          data:    (dict): The data to read from.
          path: TODO

        Returns:
          Device: Returns the created Device object.
        """
        obj = Device(Address(data['address']), path)

        obj.delta = data['delta']

        for d in data['used']:
            obj.add_entry(DeviceEntry.from_json(d))

        for d in data['unused']:
            obj.add_entry(DeviceEntry.from_json(d))

        return obj

    #-----------------------------------------------------------------------
    def __init__(self, addr, path=None):
        """Constructor
        """
        self.addr = addr
        self.save_path = path

        # All link delta number.  This is incremented by the device
        # when the db changes on the device.  It's returned in a
        # refresh (cmd=0x19) call to the device so we can check it
        # against the version we have stored.
        self.delta = None

        # Map of memory address (int) to DeviceEntry objects that are
        # active and in use.
        self.entries = {}

        # Map of memory address (int) to DeviceEntry objects that are
        # on the device but unused.  We need to keep these so we can
        # use these storage locations for future entries.
        self.unused = {}

        # Map of all link group number to DeviceEntry objects that
        # respond to that group command.
        self.groups = {}

        # Set of memory addresses that we have entries for.  This is
        # cleared when we start to download the db and used to filter
        # out duplicate entries.  Some devcies (smoke bridge) report a
        # lot of duplicate entries during db download for some reason.
        # This is the superset of addresses of self.entries and
        # self.unused.
        self._mem_locs = set()

        # Pending update function calls.  These are calls made to
        # add/del_on_device while another call is pending.  We can't
        # figure out what to do w/ the new call until the prev one
        # finishes and so we know the memory layout out the device.
        # These are function objects which are callable.
        self._pending = []

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
    def set_delta(self, delta):
        """TODO doc

        Clear the current database device delta.

        This will cause any future is_current() check to fail in order
        to force a database download.
        """
        self.delta = delta
        if delta is not None:
            self.save()

    #-----------------------------------------------------------------------
    def clear(self):
        """Clear the complete database of entries.
        """
        self.delta = None
        self.entries.clear()
        self.unused.clear()
        self.groups.clear()
        self._mem_locs.clear()

        if self.save_path and os.path.exists(self.save_path):
            os.remove(self.save_path)

    #-----------------------------------------------------------------------
    def set_path(self, path):
        """TODO: doc
        """
        self.save_path = path

    #-----------------------------------------------------------------------
    def save(self):
        """TODO: doc
        """
        assert self.save_path

        with open(self.save_path, "w") as f:
            json.dump(self.to_json(), f, indent=2)

    #-----------------------------------------------------------------------
    def __len__(self):
        return len(self.entries)

    #-----------------------------------------------------------------------
    def add_on_device(self, protocol, addr, group, data, is_controller,
                      on_done=None):
        """TODO: doc
        """
        # TODO: doc
        if not self._pending:
            self._add_on_device(protocol, addr, group, data, is_controller,
                                on_done)
        else:
            LOG.info("Device %s busy - waiting to add to db")
            func = functools.partial(self._add_on_device, protocol, addr, group,
                                     data, is_controller, on_done)
            self._pending.append(func)

    #-----------------------------------------------------------------------
    def _add_on_device(self, protocol, addr, group, data, is_controller,
                       on_done):
        # Insure types are ok - this way strings passed in from JSON
        # or MQTT get converted to the type we expect.
        addr = Address(addr)
        group = int(group)
        data = data if data else bytes(3)

        # If the record already exists, don't do anything.
        entry = self.find(addr, group, is_controller)
        if entry:
            # TODO: support checking and updating data
            LOG.warning("Device %s add db already exists for %s grp %s %s",
                        self.addr, addr, group,
                        'CTRL' if is_controller else 'RESP')
            if on_done:
                on_done(True, "Entry already exists", entry)
            return

        LOG.info("Device %s adding db: %s grp %s %s %s", self.addr, addr,
                 group, 'CTRL' if is_controller else 'RESP', data)
        assert len(self.entries)

        # Callback to remove the pending call, call the user input
        # callback if supplied, and call the next pending call if one
        # is waiting.
        def done_cb(success, msg, entry):
            LOG.debug("add_on_device done_cb %s", len(self._pending)) # TODO
            self._pending.pop(0)
            if on_done:
                on_done(success, msg, entry)

            if self._pending:
                LOG.debug("add_on_device calling next")
                self._pending[0]()

        # If there are entries in the db that are mark unused, we can
        # re-use those memory addresses and just update them w/ the
        # correct information and mark them as used.
        if self.unused:
            self._add_using_unused(protocol, addr, group, is_controller, data,
                                   done_cb)

        # If there no unused entries, we need to append one.  Write a
        # new record at the next memory location below the current
        # last entry and mark that as the new last entry.  If that
        # works, then update the record before it (the old last entry)
        # and mark it as not being the last entry anymore.  This order
        # is important since if either operation fails, the db is
        # still in a valid order.
        else:
            self._add_using_new(protocol, addr, group, is_controller, data,
                                done_cb)

        # Push a dummy pending entry to the list on the first call.
        # This way cb() has something to remove and future calls to
        # this know that there is a call in progress.
        if not self._pending:
            self._pending.append(True)

    #-----------------------------------------------------------------------
    def delete_on_device(self, protocol, entry, on_done=None):
        """TODO: doc
        """
        # TODO: doc
        if not self._pending:
            self._delete_on_device(protocol, entry, on_done)
        else:
            LOG.info("Device %s busy - waiting to delete to db")
            func = functools.partial(self._delete_on_device, protocol, entry,
                                     on_done)
            self._pending.append(func)
            return

    #-----------------------------------------------------------------------
    def _delete_on_device(self, protocol, entry, on_done):
        """TODO: doc
        """
        # see p117 of insteon dev guide: To delete a record, set the
        # in use flag in DbFlags to 0.

        # Callback to remove the pending call, call the user input
        # callback if supplied, and call the next pending call if one
        # is waiting.
        def done_cb(success, msg, entry):
            self._pending.pop(0)
            if on_done:
                on_done(success, msg, entry)

            if self._pending:
                self._pending[0]()

        # Copy the entry and mark it as unused.
        new_entry = entry.copy()
        new_entry.db_flags.in_use = False

        # Build the extended db modification message.  This says to
        # modify the entry in place w/ the new db flags which say this
        # record is no longer in use.
        ext_data = new_entry.to_bytes()
        msg = Msg.OutExtended.direct(self.addr, 0x2f, 0x00, ext_data)
        msg_handler = handler.DeviceDbModify(self, new_entry, done_cb)

        # Send the message.
        protocol.send(msg, msg_handler)

        # Push a dummy pending entry to the list on the first call.
        # This way cb() has something to remove and future calls to
        # this know that there is a call in progress.
        if not self._pending:
            self._pending.append(True)

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
        addr = Address(addr)
        group = int(group)

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
        unused = [i.to_json() for i in self.unused.values()]
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

        # Sorting by address:
        #for elem in sorted(self.entries.values(), key=lambda i: i.addr.id):

        # Sorting by memory location
        for elem in sorted(self.entries.values(), key=lambda i: i.mem_loc):
            o.write("  %s\n" % elem)

        o.write("Unused:\n")
        for elem in sorted(self.unused.values(), key=lambda i: i.mem_loc):
            o.write("  %s\n" % elem)

        o.write("GroupMap\n")
        for grp, elem in self.groups.items():
            o.write("  %s -> %s\n" % (grp, [i.addr.hex for i in elem]))

        return o.getvalue()

    #-----------------------------------------------------------------------
    def delete_entry(self, entry):
        """TODO: doc
        """
        # TODO: implement this.
        # TODO: save database
        pass

    #-----------------------------------------------------------------------
    def add_entry(self, entry):
        """TODO: doc
        """
        # Entry has a valid database entry
        if entry.db_flags.in_use:
            # NOTE: this relies on no-one keeping a handle to this
            # entry outside of this class.  This also handles
            # duplicate messages since they will have the same memory
            # location key.
            self.entries[entry.mem_loc] = entry
            self._mem_locs.add(entry.mem_loc)

            # If we're the controller for this entry, add it to the list
            # of entries for that group.
            if entry.db_flags.is_controller:
                responders = self.groups.setdefault(entry.group, [])
                if entry not in responders:
                    responders.append(entry)

        # Entry is not in use.
        else:
            # NOTE: this relies on no-one keeping a handle to this
            # entry outside of this class.  This also handles
            # duplicate messages since they will have the same memory
            # location key.
            self.unused[entry.mem_loc] = entry
            self._mem_locs.add(entry.mem_loc)

            # If the entry is a controller and it's in the group dict,
            # erase it from the group map.
            if entry.db_flags.is_controller and entry.group in self.groups:
                responders = self.groups[entry.group]
                for i in range(len(responders)):
                    if responders[i].addr == entry.addr:
                        del responders[i]
                        break

        # Save the updated database.
        self.save()

    #-----------------------------------------------------------------------
    def _add_using_unused(self, protocol, addr, group, is_controller, data,
                          on_done):
        """TODO doc
        """
        # Grab the first unused entry (highest memory address).
        entry = self.unused.pop(max(self.unused.keys()))
        LOG.info("Device %s using unused entry at mem %#06x", self.addr,
                 entry.mem_loc)

        # Update it w/ the new information.
        entry.update_from(addr, group, is_controller, data)

        # Build the extended db modification message.  This says to
        # update the record at the entry memory location.
        ext_data = entry.to_bytes()
        msg = Msg.OutExtended.direct(self.addr, 0x2f, 0x00, ext_data)
        msg_handler = handler.DeviceDbModify(self, entry, on_done)

        # Send the message and handler.
        protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def _add_using_new(self, protocol, addr, group, is_controller, data,
                       on_done):
        """TODO doc
        """
        # pylint: disable=too-many-locals

        # Memory goes high->low so find the last entry by looking
        # at the minimum value.  Then find the entry for that loc.
        last_entry = self.find_mem_loc(min(self._mem_locs))

        # Each rec is 8 bytes so move down 8 to get the next loc.
        mem_loc = last_entry.mem_loc - 0x08
        LOG.info("Device %s appending new record at mem %#06x", self.addr,
                 mem_loc)

        # Create the new entry and send it out.
        db_flags = Msg.DbFlags(in_use=True, is_controller=is_controller,
                               is_last_rec=True)
        entry = DeviceEntry(addr, group, mem_loc, db_flags, data)
        ext_data = entry.to_bytes()
        msg = Msg.OutExtended.direct(self.addr, 0x2f, 0x00, ext_data)
        msg_handler = handler.DeviceDbModify(self, entry, on_done)

        # Now create the updated current last entry w/ the last
        # record flag set to False since it's not longer last.
        # The handler will send this message out if the first call
        # above gets an ACK.
        new_last = last_entry.copy()
        new_last.db_flags.is_last_rec = False
        ext_data = new_last.to_bytes()
        next_msg = Msg.OutExtended.direct(self.addr, 0x2f, 0x00, ext_data)
        msg_handler.add_update(next_msg, new_last)

        # Send the message and handler.
        protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
