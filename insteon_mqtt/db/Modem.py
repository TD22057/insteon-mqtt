#===========================================================================
#
# Insteon PLM modem all link database
#
#===========================================================================
import io
import json
import os
from ..Address import Address
from .. import handler
from .. import log
from .. import message as Msg
from .ModemEntry import ModemEntry

LOG = log.get_logger()


class Modem:
    """Modem all link database.

    This class stores the all link database for the PLM modem.  Each
    item is a ModemEntry object that contains a single remote address,
    group, and type (controller vs responder).

    The database can be read to and written from JSOn format.
    Normally the db is constructed via message.InpAllLinkRec objects
    being read and parsed after requesting them from the modem.
    """
    @staticmethod
    def from_json(data, path):
        """Read a Modem database from a JSON input.

        The inverse of this is to_json().

        Args:
          data:    (dict): The data to read from.
          path:    (str) The file to save the database to when changes are
                   made.

        Returns:
          Modem: Returns the created Modem object.
        """
        obj = Modem(path)
        obj.entries = [ModemEntry.from_json(i) for i in data['entries']]
        return obj

    #-----------------------------------------------------------------------
    def __init__(self, path=None):
        """Constructor

        Args:
          path:  (str) The file to save the database to when changes are
                 made.
        """
        self.save_path = path

        # Note: unlike devices, the PLM has no delta value so there
        # doesn't seem to be any way to tell if the db value is
        # current or not.

        # List of ModemEntry objects in the all link database.
        self.entries = []

    #-----------------------------------------------------------------------
    def set_path(self, path):
        """Set the save path to use for the database.

        Args:
          path:   (str) The file to save the database to when changes are
                  made.
        """
        self.save_path = path

    #-----------------------------------------------------------------------
    def save(self):
        """Save the database.  A save path must have been set.
        """
        assert self.save_path

        with open(self.save_path, "w") as f:
            json.dump(self.to_json(), f, indent=2)

    #-----------------------------------------------------------------------
    def __len__(self):
        """Return the number of entries in the database.
        """
        return len(self.entries)

    #-----------------------------------------------------------------------
    def delete_entry(self, entry):
        """Remove an entry from the database without updating the device.

        After removal, the database will be saved.

        Args:
          entry:  (DeviceEntry) The entry to remove.  This entry must exist
                  or an exception is raised.
        """
        self.entries.remove(entry)
        self.save()

    #-----------------------------------------------------------------------
    def clear(self):
        """Clear the complete database of entries.

        This also removes the saved file if it exists.  It does NOT
        modify the database on the device.
        """
        self.entries = []

        if self.save_path and os.path.exists(self.save_path):
            os.remove(self.save_path)

    #-----------------------------------------------------------------------
    def find(self, addr, group, is_controller):
        """Find an entry

        Args:
          addr:           (Address) The address to match.
          group:          (int) The group to match.
          is_controller:  (bool) True for controller records.  False for
                          responder records.

        Returns:
          (ModemEntry): Returns the entry that matches or None if it
          doesn't exist.
        """
        for e in self.entries:
            if (e.addr == addr and e.group == group and
                    e.is_controller == is_controller):
                return e

        return None

    #-----------------------------------------------------------------------
    def find_all(self, addr=None, group=None, is_controller=None):
        """Find all entries that match the inputs.

        Returns all the entries that match any input that is set.  If
        an input isn't set, that field isn't checked.

        Args:
          addr:           (Address) The address to match.  None for any.
          group:          (int) The group to match.  None for any.
          is_controller:  (bool) True for controller records.  False for
                          responder records.  None for any.

        Returns:
          [ModemEntry] Returns a list of the entries that match.
        """
        addr = None if addr is None else Address(addr)
        group = None if group is None else int(group)

        results = []
        for e in self.entries:
            if addr is not None and e.addr != addr:
                continue
            if group is not None and e.group != group:
                continue
            if is_controller is not None and e.is_controller != is_controller:
                continue

            results.append(e)

        return results

    #-----------------------------------------------------------------------
    def add_on_device(self, protocol, entry, on_done=None):
        """Add an entry and push the entry to the Insteon modem.

        This sends the input record to the Insteon modem.  If that
        command succeeds, it adds the new ModemEntry record to the
        database and saves it.

        The on_done callback will be passed a success flag
        (True/False), a string message about what happened, and the
        DeviceEntry that was created (if success=True).
            on_done( success, message, ModemEntry )

        If the entry already exists, nothing will be done.

        Args:
          protocol:      (Protocol) The Insteon protocol object to use for
                         sending messages.
          entry:         (ModemEntry) The entry to add.
          on_done:       Optional callback which will be called when the
                         command completes.
        """
        exists = self.find(entry.addr, entry.group, entry.is_controller)
        if exists:
            if exists.data == entry.data:
                LOG.info("Modem.add skipping existing entry: %s", entry)
                if on_done:
                    on_done(True, "Entry already exists", exists)
                return

            cmd = Msg.OutAllLinkUpdate.Cmd.UPDATE

        elif entry.is_controller:
            cmd = Msg.OutAllLinkUpdate.Cmd.ADD_CONTROLLER

        else:
            cmd = Msg.OutAllLinkUpdate.Cmd.ADD_RESPONDER

        # Create the flags for the entry.  is_last_rec doesn't seem to
        # be used by the modem db so it's value doesn't matter.
        db_flags = Msg.DbFlags(in_use=True, is_controller=entry.is_controller,
                               is_last_rec=False)

        # Build the modem database update message.
        msg = Msg.OutAllLinkUpdate(cmd, db_flags, entry.group, entry.addr,
                                   entry.data)
        msg_handler = handler.ModemDbModify(self, entry, exists, on_done)

        # Send the message.
        protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def delete_on_device(self, protocol, addr, group, on_done=None):
        """Delete a series of entries on the device.

        This will delete ALL the entries for an address and group.
        The modem doesn't support deleting a specific controller or
        responder entry - it just deletes the first one that matches
        the address and group.  To avoid confusion about this, this
        method delete all the entries (controller and responder) that
        match the inputs.

        The on_done callback will be passed a success flag
        (True/False), a string message about what happened, and the
        DeviceEntry that was created (if success=True).
            on_done( success, message, ModemEntry )

        Args:
          protocol:      (Protocol) The Insteon protocol object to use for
                         sending messages.
          addr:          (Address) The address to delete.
          group:         (int) The group to delete.
          on_done:       Optional callback which will be called when the
                         command completes.
        """
        # The modem will delete the first entry that matches.
        entries = self.find_all(addr, group)
        if not entries:
            LOG.error("No entries matching %s grp %s", addr, group)
            if on_done:
                on_done(False, "Invalid entry to delete from modem", None)
            return

        # Modem will only delete if we pass it an empty
        # flags input (see the method docs).  This deletes the first
        # entry in the database that matches the inputs - we can't
        # select by controller or responder.
        db_flags = Msg.DbFlags.from_bytes(bytes(1))
        msg = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.DELETE, db_flags,
                                   group, addr, bytes(3))

        # Send the command once per entry in our database.  Callback
        # will remove the entry from our database if we get an ACK.
        msg_handler = handler.ModemDbModify(self, entries[0], on_done=on_done)

        # Send the first message.  If it ACK's, it will keep sending
        # more deletes - one per entry.
        protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def to_json(self):
        """Convert the database to JSON format.

        Returns:
          (dict) Returns the database as a JSON dictionary.
        """
        entries = [i.to_json() for i in self.entries]
        return {
            'entries' : entries,
            }

    #-----------------------------------------------------------------------
    def __str__(self):
        o = io.StringIO()
        o.write("ModemDb:\n")
        for entry in sorted(self.entries):
            o.write("  %s\n" % entry)

        return o.getvalue()

    #-----------------------------------------------------------------------
    def add_entry(self, entry):
        """Add a ModemEntry object to the database.

        If the entry already exists (matching address, group, and
        controller), it will be updated. It does NOT change the
        database on the Insteon device.

        Args:
          entry   (ModemEntry) The new entry.
        """
        assert isinstance(entry, ModemEntry)

        try:
            idx = self.entries.index(entry)
            self.entries[idx] = entry
        except ValueError:
            self.entries.append(entry)

        self.save()

#===========================================================================
