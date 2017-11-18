#===========================================================================
#
# Insteon PLM modem all link database
#
#===========================================================================
import io
import logging
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
    def from_json(data):
        """Read a Modem database from a JSON input.

        The inverse of this is to_json().

        Args:
          data:    (dict): The data to read from.

        Returns:
          Modem: Returns the created Modem object.
        """
        obj = Modem()
        obj.entries = [ModemEntry.from_json(i) for i in data['entries']]
        return obj

    #-----------------------------------------------------------------------
    def __init__(self):
        """Constructor
        """
        # Note: unlike devices, the PLM has no delta value so there
        # doesn't seem to be any way to tell if the db value is
        # current or not.

        # List of ModemEntry objects in the all link database.
        self.entries = []

    #-----------------------------------------------------------------------
    def __len__(self):
        return len(self.entries)

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

        entry = ModemEntry(msg.addr, msg.group, msg.flags.is_controller,
                           msg.data)
        self.add_entry(entry)

    #-----------------------------------------------------------------------
    def add_entry(self, entry):
        """Add a ModemEntry object to the database.

        If the entry already exists (matching address, group, and
        controller), it will be updated.

        Args:
          entry   (ModemEntry) The new entry.
        """
        assert isinstance(entry, ModemEntry)

        try:
            idx = self.entries.index(entry)
            self.entries[idx] = entry
        except ValueError:
            self.entries.append(entry)

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

#===========================================================================
