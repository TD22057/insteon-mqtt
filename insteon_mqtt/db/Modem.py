#===========================================================================
#
# Insteon PLM modem all link database
#
#===========================================================================
import io
import json
import logging
from ..Address import Address
from .. import handler
from .. import message as Msg
from .ModemEntry import ModemEntry

LOG = logging.getLogger(__name__)


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
          path: TODO

        Returns:
          Modem: Returns the created Modem object.
        """
        obj = Modem(path)
        obj.entries = [ModemEntry.from_json(i) for i in data['entries']]
        return obj

    #-----------------------------------------------------------------------
    def __init__(self, path=None):
        """Constructor
        """
        self.save_path = path

        # Note: unlike devices, the PLM has no delta value so there
        # doesn't seem to be any way to tell if the db value is
        # current or not.

        # List of ModemEntry objects in the all link database.
        self.entries = []

    #-----------------------------------------------------------------------
    def set_path(self, path):
        self.save_path = path

    #-----------------------------------------------------------------------
    def save(self):
        assert self.save_path

        with open(self.save_path, "w") as f:
            json.dump(self.to_json(), f, indent=2)

        LOG.info("Modem database saved %s entries", len(self))

    #-----------------------------------------------------------------------
    def __len__(self):
        return len(self.entries)

    #-----------------------------------------------------------------------
    def clear(self):
        """TODO: doc

        This does NOT update the database on the device.
        """
        self.entries = []

    #-----------------------------------------------------------------------
    def find(self, addr, group, is_controller):
        """TODO: doc
        """
        for e in self.entries:
            if (e.addr == addr and e.group == group and
                    e.is_controller == is_controller):
                return e

        return None

    #-----------------------------------------------------------------------
    def find_all(self, addr=None, group=None, is_controller=None):
        """TODO: doc
        """
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
    def add_on_device(self, protocol, entry):
        exists = self.find(entry.addr, entry.group, entry.is_controller)
        if exists:
            if exists.data == entry.data:
                LOG.info("Modem.add skipping existing entry: %s", entry)
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
        msg_handler = handler.Callback(msg, self._handle_db_update,
                                       entry=entry, exists=exists)

        # Send the message.
        protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def delete_entries(self, protocol, addr, group):
        """Delete the modem entries for an address and group.

        The modem doesn't support deleting a specific controller or
        responder entry - it just deletes the first one that matches
        the address and group.  To avoid confusion about this, this
        method delete all the entries (controller and responder) that
        match the inputs.

        TODO: doc
        """
        addr = Address(addr)
        entries = self.find_all(addr, group)
        if not entries:
            LOG.warning("Modem.delete_entries no match for %s grp %s", addr,
                        group)
            return

        # Modem will only delete if we pass it an empty flags input
        # (see the method docs).  This deletes the first entry in the
        # database that matches the inputs.
        db_flags = Msg.DbFlags.from_bytes(bytes(1))

        # Build the delete command.  When the modem replies, we'll get
        # the ack/nak.
        msg = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.DELETE, db_flags,
                                   group, addr, bytes(3))

        # Send the command once per entry in our database.  Callback
        # will remove the entry from our database if we get an ACK.
        for entry in entries:
            msg_handler = handler.Callback(msg, self._handle_delete,
                                           entry=entry)
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
    def _handle_delete(self, msg, entry):
        """TODO: doc
        """
        assert isinstance(msg, Msg.OutAllLinkUpdate)
        if msg.is_ack:
            LOG.info("Modem.delete removed entry: %s", entry)
            self.entries.remove(entry)
            self.save()
        else:
            LOG.error("Modem.delete NAK removing entry: %s", entry)

    #-----------------------------------------------------------------------
    def handle_db_rec(self, msg):
        """Handle a InpAllLinkRec database record message.

        This parses the input message into a ModemEntry record and
        adds it to the database.

        Args:
          msg:  (InpAllLinkRec) The database record to parse.
        """
        assert isinstance(msg, Msg.InpAllLinkRec)
        LOG.info("Adding modem db record for %s grp: %s", msg.addr, msg.group)

        entry = ModemEntry(msg.addr, msg.group, msg.db_flags.is_controller,
                           msg.data)
        self._add_entry(entry)
        self.save()

    #-----------------------------------------------------------------------
    def _handle_db_update(self, msg, entry, exists=None):
        """Handle a OutAllLinkUpdate database record message.

        This parses the input message into a ModemEntry record and
        adds it to the database.

        Args:
          msg:  (OutAllLinkUpdate) The database record to update.
          entry:  TODO: doc
        """
        assert isinstance(msg, Msg.OutAllLinkUpdate)

        if not msg.is_ack:
            LOG.error("Modem db updated failed: %s", msg)
            return

        # Update an existing entry w/ new data fields.
        elif msg.cmd == Msg.OutAllLinkUpdate.Cmd.UPDATE:
            LOG.info("Updating modem db record for %s grp: %s data: %s",
                     msg.addr, msg.group, msg.data)

            assert exists
            exists.data = entry.data

        # New controller or responder.
        elif (msg.cmd == Msg.OutAllLinkUpdate.Cmd.ADD_CONTROLLER or
              msg.cmd == Msg.OutAllLinkUpdate.Cmd.ADD_RESPONDER):
            LOG.info("Adding modem db record for %s type: %s grp: %s data: %s",
                     msg.addr, 'CTRL' if msg.db_flags.is_controller else
                     'RESP', msg.group, msg.data)

            self._add_entry(entry)

        else:
            LOG.error("Unexpected OutAllLinkUpdate command %s", msg.cmd)
            return

        self.save()

    #-----------------------------------------------------------------------
    def __str__(self):
        o = io.StringIO()
        o.write("ModemDb:\n")
        for entry in sorted(self.entries):
            o.write("  %s\n" % entry)

        return o.getvalue()

    #-----------------------------------------------------------------------
    def _add_entry(self, entry):
        """Add a ModemEntry object to the database.

        If the entry already exists (matching address, group, and
        controller), it will be updated.  This does NOT update the
        actual database on the device.

        Args:
          entry   (ModemEntry) The new entry.
        """
        assert isinstance(entry, ModemEntry)

        try:
            idx = self.entries.index(entry)
            self.entries[idx] = entry
        except ValueError:
            self.entries.append(entry)

#===========================================================================
