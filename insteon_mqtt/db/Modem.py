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
from .. import util
from .ModemEntry import ModemEntry
from .DbDiff import DbDiff

LOG = log.get_logger()

# First group to use for virtual scene generation.  Groups 1-8 are needed for
# simulated scenes - the modem must be a controller of a device for the
# device button group to send it a simulated scene.  So skip the first 20
# just to avoid any future items that might have more buttons.  Max scene
# number is 254 (255 is all devices).
GROUP_START = 20


class Modem:
    """Modem all link database.

    This class stores the all link database for the PLM modem.  Each item is
    a ModemEntry object that contains a single remote address, group, and
    type (controller vs responder).

    The database can be read to and written from JSOn format.  Normally the
    db is constructed via message.InpAllLinkRec objects being read and parsed
    after requesting them from the modem.
    """
    @staticmethod
    def from_json(data, path=None, device=None):
        """Read a Modem database from a JSON input.

        The inverse of this is to_json().

        Args:
          data:    (dict): The data to read from.
          path:    (str) The file to save the database to when changes are
                   made.
          device:  (Modem): The Modem device object

        Returns:
          Modem: Returns the created Modem object.
        """
        obj = Modem(path, device)
        for d in data['entries']:
            obj.add_entry(ModemEntry.from_json(d, db=obj), save=False)

        # pylint: disable=protected-access
        obj._meta = data.get('meta', {})

        return obj

    #-----------------------------------------------------------------------
    def __init__(self, path=None, device=None):
        """Constructor

        Args:
          path:  (str) The file to save the database to when changes are made.
          device: (Modem) The Modem device object.
        """
        self.save_path = path

        # Note: unlike devices, the PLM has no delta value so there doesn't
        # seem to be any way to tell if the db value is current or not.

        # Metadata storage.  Used for saving device data to persistent
        # storage for access across reboots
        self._meta = {}

        # List of ModemEntry objects in the all link database.
        self.entries = []

        # Map of all link group number to ModemEntry objects that respond to
        # that group command.
        self.groups = {}

        # Map of string scene names to integer controller groups
        self.aliases = {}

        # Link to the Modem device
        self.device = device

    #-----------------------------------------------------------------------
    def set_path(self, path):
        """Set the save path to use for the database.

        Args:
          path:   (str) The file to save the database to when changes are
                  made.
        """
        self.save_path = path

    #-----------------------------------------------------------------------
    def set_meta(self, key, value):
        """Set the metadata key to value.

        Used for saving device parameters to persistent storage between
        reboots.

        Args:
          key:    A valid python dictionary key to store the value
          value:  A data type capable of being represented in json
        """
        self._meta[key] = value
        self.save()

    #-----------------------------------------------------------------------
    def get_meta(self, key):
        """Get the metadata key value.

        Used for getting device parameters from persistent storage between
        reboots.

        Args:
          key:    A valid python dictionary key to retreive the value from
        """
        return self._meta.get(key, None)

    #-----------------------------------------------------------------------
    def save(self):
        """Save the database.

        If a save path wasn't set, nothing is done.
        """
        if not self.save_path:
            return

        with open(self.save_path, "w") as f:
            json.dump(self.to_json(), f, indent=2)

    #-----------------------------------------------------------------------
    def __len__(self):
        """Return the number of entries in the database.
        """
        return len(self.entries)

    #-----------------------------------------------------------------------
    def next_group(self):
        """Find the next free internal PLM group number that is available.

        This is used to find an available group number for creating a virtual
        modem scene.  The modem supports 1-255 for groups.  Groups 1-8 are
        needed for simulated scenes - the modem must be a controller of a
        device for the device button group to send it a simulated scene.

        Returns:
          (int) Returns the next group number of None if there are none.
        """
        for i in range(GROUP_START, 255):
            if i not in self.groups:
                return i

        return None

    #-----------------------------------------------------------------------
    def delete_entry(self, entry):
        """Remove an entry from the database without updating the device.

        After removal, the database will be saved.

        Args:
          entry:  (DeviceEntry) The entry to remove.  This entry must exist
                  or an exception is raised.
        """
        self.entries.remove(entry)

        if entry.is_controller:
            responders = self.groups.get(entry.group)
            if responders:
                if entry in responders:
                    responders.remove(entry)

            elif entry.group in self.groups:
                del self.groups[entry.group]

        self.save()

    #-----------------------------------------------------------------------
    def clear(self):
        """Clear the complete database of entries.

        This also removes the saved file if it exists.  It does NOT modify
        the database on the device.
        """
        self.entries = []
        self.groups = {}
        self.aliases = {}
        self._meta = {}

        if self.save_path and os.path.exists(self.save_path):
            os.remove(self.save_path)

    #-----------------------------------------------------------------------
    def find_group(self, group):
        """Find all the database entries in a group.

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

        Returns all the entries that match any input that is set.  If an
        input isn't set, that field isn't checked.

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
    def add_on_device(self, entry, on_done=None):
        """Add an entry and push the entry to the Insteon modem.

        This sends the input record to the Insteon modem.  If that command
        succeeds, it adds the new ModemEntry record to the database and saves
        it.

        The on_done callback will be passed a success flag (True/False), a
        string message about what happened, and the DeviceEntry that was
        created (if success=True).
          on_done( success, message, ModemEntry )

        If the entry already exists, nothing will be done.

        Args:
          entry:         (ModemEntry) The entry to add.
          on_done:       Optional callback which will be called when the
                         command completes.
        """
        exists = self.find(entry.addr, entry.group, entry.is_controller)
        if exists:
            if exists.data == entry.data:
                LOG.warning("Modem add db already exists for %s grp %s %s",
                            entry.addr, entry.group,
                            util.ctrl_str(entry.is_controller))
                if on_done:
                    on_done(True, "Entry already exists", exists)
                return

            cmd = Msg.OutAllLinkUpdate.Cmd.UPDATE

        elif entry.is_controller:
            cmd = Msg.OutAllLinkUpdate.Cmd.ADD_CONTROLLER

        else:
            cmd = Msg.OutAllLinkUpdate.Cmd.ADD_RESPONDER

        # Create the flags for the entry.  is_last_rec doesn't seem to be
        # used by the modem db so it's value doesn't matter.
        db_flags = Msg.DbFlags(in_use=True, is_controller=entry.is_controller,
                               is_last_rec=False)

        # Build the modem database update message.
        msg = Msg.OutAllLinkUpdate(cmd, db_flags, entry.group, entry.addr,
                                   entry.data)
        msg_handler = handler.ModemDbModify(self, entry, exists, on_done)

        # Send the message.
        self.device.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def delete_on_device(self, entry, on_done=None):
        """Delete a series of entries on the device.

        This will delete ALL the entries for an address and group.  The modem
        doesn't support deleting a specific controller or responder entry -
        it just deletes the first one that matches the address and group.  To
        avoid confusion about this, this method delete all the entries
        (controller and responder) that match the inputs.

        The on_done callback will be passed a success flag (True/False), a
        string message about what happened, and the DeviceEntry that was
        created (if success=True).
          on_done( success, message, ModemEntry )

        Args:
          addr:          (Address) The address to delete.
          group:         (int) The group to delete.
          on_done:       Optional callback which will be called when the
                         command completes.
        """
        on_done = util.make_callback(on_done)

        # Find all the entries that match the addr and group inputs.
        entries = self.find_all(entry.addr, entry.group)

        # The modem will erase entries in the order it finds them - we can't
        # erase a specific entry.  So find the ctrl/resp entry we want and
        # see if there is a different entry first - if there is call delete
        # until we delete the one we actually want and then restore the other
        # entry after we're done.
        #
        # In a proper database, we should only have found 1 or 2 entries but
        # it's possible to push duplicate records into the db.  So just find
        # the first entry that matches our request and only restore one other
        # which which be the opposite ctrl/responder flag version.
        restore = None
        erase_idx = None
        for i in range(len(entries)):
            if entries[i].is_controller == entry.is_controller:
                erase_idx = i
                break

            if not restore:
                restore = entries[i]

        # Since the entry was passed in, it must exist.
        assert erase_idx is not None

        LOG.debug("Modem delete idx %d of [0,%d) entries", erase_idx,
                  len(entries))

        # Build the first delete message.  The Handler will remove the
        # entries from our db when it get's an ACK.
        #
        # Modem will only delete if we pass it an empty flags input (see the
        # method docs).  This deletes the first entry in the database that
        # matches the inputs.
        db_flags = Msg.DbFlags.from_bytes(bytes(1))
        msg = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.DELETE, db_flags,
                                   entry.group, entry.addr, bytes(3))
        msg_handler = handler.ModemDbModify(self, entries[0], on_done=on_done)

        # Add the other delete calls to the handler - these will run in
        # sequence as we get ACKs for each call.  The final call will call
        # the on_done() callback.
        for i in range(1, erase_idx + 1):
            msg_handler.add_update(msg, entries[i])

        # Add a command to restore the entry we didn't want to delete.
        if restore:
            if restore.is_controller:
                cmd = Msg.OutAllLinkUpdate.Cmd.ADD_CONTROLLER
            else:
                cmd = Msg.OutAllLinkUpdate.Cmd.ADD_RESPONDER

            msg2 = Msg.OutAllLinkUpdate(cmd, db_flags, restore.group,
                                        restore.addr, restore.data)
            msg_handler.add_update(msg2, restore)

        # Send the first message.  If it ACK's, it will keep sending more
        # deletes - one per entry.
        self.device.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def diff(self, rhs):
        """Compare this database with another Modem database.

        It's an error (logged and will return None) to use this on databases
        other than for the modem.  The purpose of this method is to compare
        two database for the same modem and generate a list of commands that
        will cause the input rhs database to be equal to the self database.

        The return value is a db.DbDiff object that contains the
        additions and deletions needed to update rhs to match self.

        Args:
           rhs:   (db.Modem) The other device db to compare with.

        Returns:
           Returns the list changes needed in rhs to make it equal to this
           object.
        """
        if not isinstance(rhs, Modem):
            LOG.error("Error trying to compare modem databases for %s vs"
                      " %s.  Only the same device can be differenced.",
                      type(self).__name__, type(rhs).__name__)
            return None

        # Copy the rhs entry list of ModemEntry.  For each match
        # that we find, we'll remove that address from the dict.  The result
        # will be the entries that need to be removed from rhs to make it
        # match.
        rhsRemove = rhs.entries.copy()

        delta = DbDiff(None)  # Modem db doesn't have addr
        for entry in self.entries:
            rhsEntry = rhs.find(entry.addr, entry.group, entry.is_controller)

            # RHS is missing this entry
            # The Modem Data bytes never matter, we ignore them entirely
            if rhsEntry is None:
                # Ignore certain links created by 'join' or 'pair'
                # See notes below.
                if not entry.is_controller:
                    # This is a link from the pair command
                    pass
                elif (entry.is_controller and
                      entry.group in (0x00, 0x01)):
                    # This is a link from the join command
                    pass
                else:
                    delta.add(entry)

            # Otherwise this is match so we can note that from the list
            # if it is there.  If there are duplicates on the left hand side,
            # may already have been removed
            elif rhsEntry and rhsEntry in rhsRemove:
                rhsRemove.remove(rhsEntry)

        # Ignore certain links created by 'join' or 'pair'
        # #1 any responder link from a valid device.  These are normally
        # created by the 'pair' command.  There is currently no way to know the
        # groups that should exist on a device.  So we ignore all, but in the
        # future may want to add something to each device so that we can delete
        # erroneous entries.
        # #2 any controller links from group 0x01 or 0x02 to a valid device,
        # these are results from the 'join' command
        for entry in list(rhsRemove):
            if (not entry.is_controller and
                    rhs.device.find(entry.addr) is not None):
                rhsRemove.remove(entry)
            if (entry.is_controller and entry.group in (0x00, 0x01) and
                    rhs.device.find(entry.addr) is not None):
                rhsRemove.remove(entry)

        # Add in remaining rhs entries that where not matches as entries that
        # need to be removed.
        for entry in rhsRemove:
            delta.remove(entry)

        return delta

    #-----------------------------------------------------------------------
    def to_json(self):
        """Convert the database to JSON format.

        Returns:
          (dict) Returns the database as a JSON dictionary.
        """
        entries = [i.to_json() for i in self.entries]
        return {
            'entries' : entries,
            'meta' : self._meta
            }

    #-----------------------------------------------------------------------
    def __str__(self):
        o = io.StringIO()
        o.write("ModemDb:\n")
        for entry in sorted(self.entries):
            o.write("  %s\n" % entry)

        o.write("GroupMap\n")
        for grp, elem in self.groups.items():
            o.write("  %s -> %s\n" % (grp, [i.label for i in elem]))

        return o.getvalue()

    #-----------------------------------------------------------------------
    def add_entry(self, entry, save=True):
        """Add a ModemEntry object to the database.

        If the entry already exists (matching address, group, and
        controller), it will be updated. It does NOT change the database on
        the Insteon device.

        Args:
          entry   (ModemEntry) The new entry.
        """
        assert isinstance(entry, ModemEntry)

        try:
            idx = self.entries.index(entry)
            self.entries[idx] = entry
        except ValueError:
            self.entries.append(entry)

        # If we're the controller for this entry, add it to the list of
        # entries for that group.
        if entry.is_controller:
            responders = self.groups.setdefault(entry.group, [])
            if entry not in responders:
                responders.append(entry)

        if save:
            self.save()

    #-----------------------------------------------------------------------
    def add_from_config(self, remote, local):
        """Add an entry to the config database from the config file.

        Is called by _load_scenes() on the modem.  Adds an entry to the next
        available mem_loc from an entry specified in the config file.  This
        should only be used to add an entry to a db_config database, which is
        then compared with the actual database using diff().

        Args:
          remote (SceneDevice): The remote device to link to
          local (SceneDevice): The local device link pair of this entry
        """

        # Generate the entry
        group = local.group
        if remote.is_controller:
            group = remote.group
        entry = ModemEntry(remote.addr, group, local.is_controller,
                           local.link_data, db=self)

        # Add the Entry to the DB
        self.add_entry(entry, save=False)

#===========================================================================
