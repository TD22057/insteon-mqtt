#===========================================================================
#
# Non-modem device all link database class
#
#===========================================================================
import io
import itertools
import json
import os
from ..Address import Address
from .. import catalog
from ..CommandSeq import CommandSeq
from .. import handler
from .DeviceEntry import DeviceEntry
from .DbDiff import DbDiff
from .. import log
from .. import message as Msg
from .. import util
from .DeviceModifyManagerI1 import DeviceModifyManagerI1

LOG = log.get_logger()

# From the docs - initial memory location for the entries.  Each entry is 8
# bytes and moves down from this (0x0fff, 0x0ff7, ...)
START_MEM_LOC = 0x0fff


class Device:
    """Device all link database.

    This class stores the all link database for an Insteon device.  Each item
    is a DeviceEntry object that contains a single remote address, group, and
    type (controller vs responder).

    The database can be read to and written from JSOn format.  Normally the
    db is constructed via message.InpExtended objects being read and parsed
    after requesting them from the device.

    Insteon devices use a "delta" to record the revision of the database on
    the device.  This class stores that as well so we know if the database is
    out of date with the one on the Insteon device.
    """

    @staticmethod
    def from_json(data, path, device):
        """Read a Device database from a JSON input.

        The inverse of this is to_json().

        Args:
          data:   (dict) The data to read from.
          path:   (str) The file to save the database to when changes are
                  made.
          device: (Device) The device object.
        Returns:
          Device: Returns the created Device object.
        """
        # Create the basic database object.
        obj = Device(Address(data['address']), path, device)

        # Extract the various files from the JSON data.
        obj.delta = data['delta']
        obj.engine = data.get('engine', None)

        # Load the category fields and turn them into description objecdt.
        dev_cat = data.get('dev_cat', None)
        sub_cat = data.get('sub_cat', None)
        obj.desc = None
        if dev_cat:
            obj.desc = catalog.find(dev_cat, sub_cat)

        obj.firmware = data.get('firmware', None)
        # pylint: disable=protected-access
        obj._meta = data.get('meta', {})

        for d in data['used']:
            obj.add_entry(DeviceEntry.from_json(d), save=False)

        for d in data['unused']:
            obj.add_entry(DeviceEntry.from_json(d), save=False)

        if "last" in data:
            obj.last = DeviceEntry.from_json(data["last"])

        # When loading db's <= ver 0.6, no last field was saved to create
        # one at the correct location.
        if obj.last.mem_loc == START_MEM_LOC and len(obj):
            for e in itertools.chain(obj.entries.values(),
                                     obj.unused.values()):
                obj.last.mem_loc = min(obj.last.mem_loc, e.mem_loc)

            obj.last.mem_loc -= 0x08

        return obj

    #-----------------------------------------------------------------------
    def __init__(self, addr, path=None, device=None):
        """Constructor

        Args:
          addr:  (Address) The Insteon address of the device the database
                 is for.
          path:  (str) The file to save the database to when changes are
                 made.
          device: (Device) The device object.
        """
        self.addr = addr
        self.save_path = path

        # All link delta number.  This is incremented by the device when the
        # db changes on the device.  It's returned in a refresh (cmd=0x19)
        # call to the device so we can check it against the version we have
        # stored.
        self.delta = None

        # Engine version.  0 is i1, 1 is i2, 2 is i2cs.  It is obtained from
        # a get_engine request (cmd=0x0D).  Most of the code assumes
        # relatively new devices (engine 2) but we'll leave it set as None
        # here to show that we haven't checked the engine version yet.
        self.engine = None

        # Device model information.
        self.desc = None
        self.firmware = None

        # Metadata storage.  Used for saving device data to persistent
        # storage for access across reboots
        self._meta = {}

        # Map of memory address (int) to DeviceEntry objects that are active
        # and in use.
        self.entries = {}

        # Map of memory address (int) to DeviceEntry objects that are on the
        # device but unused.  We need to keep these so we can use these
        # storage locations for future entries.  This does not include the
        # last entry in the db.
        self.unused = {}

        # The last entry in the database.  Devices show an unused, null (all
        # zeros) marked with the LAST bit set in the db.  From the docs this
        # shouldn't be required - the LAST bit can be a usable entry but it
        # doesn't appear to work.  So this is a null entry with the LAST bit
        # set.  It's also the mem loc of the next entry to append to the db
        # when adding a new entry.
        flags = Msg.DbFlags(in_use=False, is_controller=False,
                            is_last_rec=True)
        self.last = DeviceEntry(Address(0, 0, 0), 0, START_MEM_LOC, flags,
                                None)

        # Map of all link group number to DeviceEntry objects that respond to
        # that group command.
        self.groups = {}

        # Link to the Modem device
        self.device = device

    #-----------------------------------------------------------------------
    def is_current(self, delta):
        """See if the database is current.

        The current delta is reported in the device status messages.  Compare
        that against the stored delta in the database to see if this database
        is current.  If it's not, a new database needs to be downloaded from
        the device.

        Args:
          delta:  (int) The database delta to check

        Returns:
          (bool) Returns True if the database delta matches the input.
        """
        return delta == self.delta

    #-----------------------------------------------------------------------
    def set_delta(self, delta):
        """Set the current database delta.

        This records the input delta as the current value.  If the input
        isn't None, the database is also saved to record this value.

        Args:
          delta:  (int) The database delta.  None to clear the delta.
        """
        self.delta = delta
        if delta is not None:
            self.save()

    #-----------------------------------------------------------------------
    def set_engine(self, engine):
        """Set the device engine version.

        This records the engine version of the device. 0 is i1, 1 is i2 and
        2 is i2cs

        Args:
          engine:  (int) The engine version.  None to clear the engine.
        """
        self.engine = engine
        if engine is not None:
            self.save()

    #-----------------------------------------------------------------------
    def set_info(self, dev_cat, sub_cat, firmware):
        """Saves the device information to file.

        Insteon devices are each assigned to a broad device category.
        Individual devices each then have a subcategory.  See the catalog.py
        module for details.

        Within the broad device category, insteon devices are assigned to a
        more narrow sub category.  Generally a sub-category remains
        consistent throughout a single model number of a a product, however
        not always.  Smart Labs has done a poor job of publishing the details
        of the sub-categories.  Some resources for determining the details of
        a sub-category are:

        http://cache.insteon.com/pdf/INSTEON_DevCats_and_Product_Keys_20081008.pdf
        http://madreporite.com/insteon/Insteon_device_list.htm

        Generally knowing the dev_Cat and sub_Cat is sufficient for
        determining the features that are available on a device.
        Additionally knowing the engine version of the device is also another
        good indicator.

        The firmware version of a device is just that, the version number of
        the embedded code on the device.  In theory, this firmware is
        updatable (although not by a casual user), however Smart Labs has
        never published an update for any device.

        That said, it does seem that Smart Labs routinely updates the
        firmware that is installed on devices before they are sold.  However,
        Smart Labs does not publish changelogs, nor does it discuss what
        changes have been made.  Based on anecdotal evidence, few if any
        changes in firmware have added any features to a device.

        Args:
          dev_cat (int):  The device category.
          sub_cat (int):  The device sub-category.
          firmware (int): The device firmware.
        """
        self.desc = catalog.find(dev_cat, sub_cat)
        self.firmware = firmware
        self.save()

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
    def clear(self):
        """Clear the complete database of entries.

        This also removes the saved file if it exists.  It does NOT modify
        the database on the device.
        """
        self.delta = None
        self.entries.clear()
        self.unused.clear()
        self.groups.clear()
        self.last.mem_loc = START_MEM_LOC

        if self.save_path and os.path.exists(self.save_path):
            os.remove(self.save_path)

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
    def add_on_device(self, device, addr, group, is_controller, data,
                      on_done=None):
        """Add an entry and push the entry to the Insteon device.

        This sends the input record to the Insteon device.  If that command
        succeeds, it adds the new DeviceEntry record to the database and
        saves it.

        IMPORTANT: Multiple calls to this method are NOT possible.  You must
        chain calls together using a CommandSeq object to insure that the
        first call finishes before another one is made.

        The on_done callback will be passed a success flag (True/False), a
        string message about what happened, and the DeviceEntry that was
        created (if success=True).
           on_done( success, message, DeviceEntry )

        Args:
          device:        (device.Base) The Insteon device object to use for
                         sending messages.
          addr:          (Address) The address of the device in the database.
          group:         (int) The group the entry is for.
          is_controller: (bool) True if the device is a controller.
          data:          (bytes) 3 data bytes.  [0] is the on level, [1] is the
                         ramp rate.
          on_done:       Optional callback which will be called when the
                         command completes.
        """
        # Insure types are ok - this way strings passed in from JSON or MQTT
        # get converted to the type we expect.
        addr = Address(addr)
        group = int(group)
        data = data if data else bytes(3)
        on_done = util.make_callback(on_done)

        # See if we can fill in an unused entry in the db.
        add_unused = len(self.unused) > 0

        # See if the entry already exists.
        entry = self.find(addr, group, is_controller)

        # If the entry exists, but has different data, pretend it's unused so
        # we'll overwrite that memory location.
        if entry and entry.data != data:
            add_unused = True

        # Otherwise, we don't need to do anything - the entry exists.
        elif entry:
            LOG.warning("Device %s add db already exists for %s grp %s %s",
                        self.addr, addr, group, util.ctrl_str(is_controller))
            on_done(True, "Entry already exists", entry)
            return

        LOG.info("Device %s adding db: %s grp %s %s %s", self.addr, addr,
                 group, util.ctrl_str(is_controller), data)

        # If there are entries in the db that are mark unused, we can re-use
        # those memory addresses and just update them w/ the correct
        # information and mark them as used.
        if add_unused:
            self._add_using_unused(device, addr, group, is_controller, data,
                                   on_done, entry)

        # If there no unused entries, we need to append one.  Write a new
        # record at the next memory location below the current last entry and
        # mark that as the new last entry.  If that works, then update the
        # record before it (the old last entry) and mark it as not being the
        # last entry anymore.  This order is important since if either
        # operation fails, the db is still in a valid order.
        else:
            self._add_using_new(device, addr, group, is_controller, data,
                                on_done)

    #-----------------------------------------------------------------------
    def delete_on_device(self, device, entry, on_done=None):
        """Delete an entry on the Insteon device.

        This sends the deletes the input record from the Insteon device.  If
        that command succeeds, it removes the DeviceEntry record to the
        database and saves it.

        IMPORTANT: Multiple calls to this method are NOT possible.  You must
        chain calls together using a CommandSeq object to insure that the
        first call finishes before another one is made.

        The on_done callback will be passed a success flag (True/False), a
        string message about what happened, and the DeviceEntry that was
        created (if success=True).
           on_done( success, message, DeviceEntry )

        Args:
          device:        (device.Base) The Insteon device object to use for
                         sending messages.
          entry:         (DeviceEntry) The entry to remove.
          on_done:       Optional callback which will be called when the
                         command completes.
         """
        # see p117 of insteon dev guide: To delete a record, set the in use
        # flag in DbFlags to 0.

        # Copy the entry and mark it as unused.
        new_entry = entry.copy()
        new_entry.db_flags.in_use = False

        if self.engine == 0:
            modify_manager = DeviceModifyManagerI1(device, self,
                                                   new_entry, on_done=on_done,
                                                   num_retry=3)
            modify_manager.start_modify()
        else:
            # Build the extended db modification message.  This says to
            # modify the entry in place w/ the new db flags which say this
            # record is no longer in use.
            ext_data = new_entry.to_bytes()
            msg = Msg.OutExtended.direct(self.addr, 0x2f, 0x00, ext_data)
            msg_handler = handler.DeviceDbModify(self, new_entry, on_done)

            # Send the message.
            device.send(msg, msg_handler)

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
          (DeviceEntry): Returns the entry that matches or None if it
          doesn't exist.
        """
        # Convert to formal values - allows for string inputs for the address
        # for example.
        addr = Address(addr)
        group = int(group)

        for e in self.entries.values():
            if (e.addr == addr and e.group == group and
                    e.is_controller == is_controller):
                return e

        return None

    #-----------------------------------------------------------------------
    def find_mem_loc(self, mem_loc):
        """Find an entry by memory location.

        Args:
          mem_loc:  (int) The memory address to find.

        Returns:
          (DeviceEntry): Returns the entry or None if it doesn't exist.
        """
        return self.entries.get(mem_loc, None)

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
          [DeviceEntry] Returns a list of the entries that match.
        """
        addr = None if addr is None else Address(addr)
        group = None if group is None else int(group)

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
    def diff(self, rhs):
        """Compare this database with another Device database.

        It's an error (logged and will return None) to use this on databases
        for difference addresses.  The purpose of this method is to compare
        two database for the same device and generate a list of commands that
        will cause the input rhs database to be equal to the self database.

        The return value is a db.DbDiff object that contains the
        additions and deletions needed to update rhs to match self.

        Args:
           rhs:   (db.Device) The other device db to compare with.

        Returns:
           Returns the list changes needed in rhs to make it equal to this
           object.
        """
        if self.addr != rhs.addr:
            LOG.error("Error trying to compare device databases for %s vs"
                      " %s.  Only the same device can be differenced.",
                      self.addr, rhs.addr)
            return None

        # Copy the rhs entry dict of mem_loc->DeviceEntry.  For each match
        # that we find, we'll remove that address from the dict.  The result
        # will be the entries that need to be removed from rhs to make it
        # match.
        rhsRemove = {k : v for k, v in rhs.entries.items()}

        delta = DbDiff(self.addr)
        for entry in self.entries.values():
            rhsEntry = rhs.find(entry.addr, entry.group, entry.is_controller)

            # RHS is missing this entry or has different data bytes we need
            # to update.
            if rhsEntry is None or not entry.identical(rhsEntry):
                # Ignore certain links created by 'join' or 'pair'
                # See notes below.
                if (entry.is_controller and
                        entry.addr == self.device.modem.addr):
                    # This is a link from the pair command
                    pass
                elif (not entry.is_controller and
                      entry.group in (0x00, 0x01) and
                      entry.addr == self.device.modem.addr):
                    # This is a link from the join command
                    pass
                else:
                    delta.add(entry)

            # Otherwise this is match so we can note that by removing this
            # address from the set, if it is there.  If there are duplicates
            # on the left hand side, this address may already have been removed
            elif rhsEntry and rhsEntry.mem_loc in rhsRemove:
                del rhsRemove[rhsEntry.mem_loc]

        # Ignore certain links created by 'join' or 'pair'
        # #1 any controller link to the modem.  These are normally
        # created by the 'pair' command.  There is currently no way to know the
        # groups that should exist on a device.  So we ignore all, but in the
        # future may want to add something to each device so that we can delete
        # erroneous entries.
        # #2 any responder links from the modem for groups 0x01 or 0x02,
        # these are results from the 'join' command
        for _addr in list(rhsRemove):
            entry = rhsRemove[_addr]
            if entry.is_controller and entry.addr == rhs.device.modem.addr:
                del rhsRemove[_addr]
            if (not entry.is_controller and entry.group in (0x00, 0x01) and
                    entry.addr == rhs.device.modem.addr):
                del rhsRemove[_addr]

        # Add in remaining rhs entries that where not matches as entries that
        # need to be removed.
        for entry in rhsRemove.values():
            delta.remove(entry)

        return delta

    #-----------------------------------------------------------------------
    def apply_diff(self, device, diff, on_done=None):
        """TODO: doc
        """
        assert self.addr == diff.addr

        seq = CommandSeq(device, "Device database sync complete", on_done)

        # Start by removing all the entries we don't need.  This way we free
        # up memory locations to use for the add.
        for entry in diff.del_entries:
            seq.add(self.delete_on_device, entry)

        # Add the missing entries.
        for entry in diff.add_entries:
            seq.add(self.add_on_device, device, entry.addr, entry.group,
                    entry.is_controller, entry.data)

        seq.run()

    #-----------------------------------------------------------------------
    def to_json(self):
        """Convert the database to JSON format.

        Returns:
          (dict) Returns the database as a JSON dictionary.
        """
        used = [i.to_json() for i in self.entries.values()]
        unused = [i.to_json() for i in self.unused.values()]
        data = {
            'address' : self.addr.to_json(),
            'delta' : self.delta,
            'engine' : self.engine,
            'dev_cat' : None,
            'sub_cat' : None,
            'firmware' : self.firmware,
            'used' : used,
            'unused' : unused,
            'last' : self.last.to_json(),
            'meta' : self._meta
            }
        if self.desc:
            data['dev_cat'] = self.desc.dev_cat
            data['sub_cat'] = self.desc.sub_cat

        return data

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

        if self.last:
            o.write("Last:\n")
            o.write("  %s\n" % self.last)

        o.write("GroupMap\n")
        for grp, elem in self.groups.items():
            o.write("  %s -> %s\n" % (grp, [i.addr.hex for i in elem]))

        return o.getvalue()

    #-----------------------------------------------------------------------
    def add_entry(self, entry, save=True):
        """Add an entry to the database without updating the device.

        This is used when reading entries from disk.  It does NOT change the
        database on the Insteon device.

        Args:
          entry:  (DeviceEntry) The entry to add.
        """
        # Entry is an active entry.
        if entry.db_flags.in_use:
            # NOTE: this relies on no-one keeping a handle to this entry
            # outside of this class.  This also handles duplicate messages
            # since they will have the same memory location key.  Pop this
            # address off unused to insure both dicts stay in sync.
            self.entries[entry.mem_loc] = entry
            self.unused.pop(entry.mem_loc, None)

            # If we're the controller for this entry, add it to the list of
            # entries for that group.
            if entry.db_flags.is_controller:
                responders = self.groups.setdefault(entry.group, [])
                if entry not in responders:
                    responders.append(entry)

        # Entry is not in use and is a new last record to use
        elif entry.db_flags.is_last_rec:
            self.last = entry

        # Entry is a normal record but is not in use.
        else:
            # NOTE: this relies on no one keeping a handle to this entry
            # outside of this class.  This also handles duplicate messages
            # since they will have the same memory location key.  Pop this
            # address off entries to insure both dicts stay in sync.
            self.unused[entry.mem_loc] = entry
            self.entries.pop(entry.mem_loc, None)

            # If the entry is a controller and it's in the group dict, erase
            # it from the group map.
            if entry.db_flags.is_controller and entry.group in self.groups:
                responders = self.groups[entry.group]
                for i in range(len(responders)):
                    if responders[i].mem_loc == entry.mem_loc:
                        del responders[i]
                        break

        # Save the updated database.
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
        # Get the mem_loc and move last entry down 1 position
        mem_loc = self.last.mem_loc
        self.last.mem_loc -= 0x08

        # Generate the entry
        db_flags = Msg.DbFlags(in_use=True, is_controller=local.is_controller,
                               is_last_rec=False)
        group = local.group
        if remote.is_controller:
            group = remote.group
        entry = DeviceEntry(remote.addr, group, mem_loc, db_flags,
                            local.link_data)

        # Add the Entry to the DB
        self.add_entry(entry, save=False)

    #-----------------------------------------------------------------------
    def _add_using_unused(self, device, addr, group, is_controller, data,
                          on_done, entry=None):
        """Add an entry using an existing, unused entry.

        Grabs the first entry w/ the used flag=False and tells the device to
        update that record.
        """
        # Grab the first unused entry (highest memory address).
        if not entry:
            entry = self.unused.pop(max(self.unused.keys()))
        LOG.info("Device %s using unused entry at mem %#06x", self.addr,
                 entry.mem_loc)

        # Update it w/ the new information.
        entry.update_from(addr, group, is_controller, data)

        if self.engine == 0:
            modify_manager = DeviceModifyManagerI1(device, self,
                                                   entry, on_done=on_done,
                                                   num_retry=3)
            modify_manager.start_modify()
        else:
            # Build the extended db modification message.  This says to update
            # the record at the entry memory location.
            ext_data = entry.to_bytes()
            msg = Msg.OutExtended.direct(self.addr, 0x2f, 0x00, ext_data)
            msg_handler = handler.DeviceDbModify(self, entry, on_done)

            # Send the message and handler.
            device.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def _add_using_new(self, device, addr, group, is_controller, data,
                       on_done):
        """Add a anew entry at the end of the database.

        First we send the new entry to the remote device.  If that works,
        then we update the previously last entry to mart it as "not the last
        entry" so the device knows there is one more record.
        """
        # pylint: disable=too-many-locals

        # Start by moving the current last record down 8 bytes.  Write out
        # the new last record and then create a new record with the input
        # data at the location of the old last record.
        LOG.info("Device %s appending new record at mem %#06x", self.addr,
                 self.last.mem_loc)

        seq = CommandSeq(device, "Device database update complete", on_done)

        # Shift the current last record down 8 bytes.  Make a copy - we'll
        # only update our member var if the write works.
        last = self.last.copy()
        last.mem_loc -= 0x08

        # Start by writing the last record - that way if it fails, we don't
        # try and update w/ the new data record.
        if self.engine == 0:
            # on_done is passed by the sequence manager inside seq.add()
            modify_manager = DeviceModifyManagerI1(device, self,
                                                   last, on_done=None,
                                                   num_retry=3)
            seq.add(modify_manager.start_modify)
        else:
            ext_data = last.to_bytes()
            msg = Msg.OutExtended.direct(self.addr, 0x2f, 0x00, ext_data)
            msg_handler = handler.DeviceDbModify(self, last)
            seq.add_msg(msg, msg_handler)

        # Create the new entry at the current last memory location.
        db_flags = Msg.DbFlags(in_use=True, is_controller=is_controller,
                               is_last_rec=False)
        entry = DeviceEntry(addr, group, self.last.mem_loc, db_flags, data)

        if self.engine == 0:
            # on_done is passed by the sequence manager inside seq.add()
            modify_manager = DeviceModifyManagerI1(device, self,
                                                   entry, on_done=None,
                                                   num_retry=3)
            seq.add(modify_manager.start_modify)
        else:
            # Add the call to update the data record.
            ext_data = entry.to_bytes()
            msg = Msg.OutExtended.direct(self.addr, 0x2f, 0x00, ext_data)
            msg_handler = handler.DeviceDbModify(self, entry)
            seq.add_msg(msg, msg_handler)

        seq.run()

    #-----------------------------------------------------------------------
