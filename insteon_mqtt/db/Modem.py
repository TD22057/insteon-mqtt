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
    @staticmethod
    def from_json(data):
        obj = Modem()
        obj.entries = [ModemEntry.from_json(i) for i in data['entries']]
        return obj

    #-----------------------------------------------------------------------
    def __init__(self):
        # Note: unlike devices, the PLM has no delta value so there
        # doesn't seem to be any way to tell if the db value is
        # current or not.

        # List of ModemEntry objects in the all link database.
        self.entries = []

    #-----------------------------------------------------------------------
    def __len__(self):
        return len(self.entries)

    #-----------------------------------------------------------------------
    def add(self, msg):
        assert isinstance(msg, Msg.InpAllLinkRec)
        LOG.info("Adding modem db record for %s grp: %s", msg.addr, msg.group)

        entry = ModemEntry(msg.addr, msg.group, msg.flags.is_controller,
                           msg.data)
        self.add_entry(entry)

    #-----------------------------------------------------------------------
    def add_entry(self, entry):
        assert isinstance(entry, ModemEntry)

        try:
            idx = self.entries.index(entry)
            self.entries[idx] = entry
        except ValueError:
            self.entries.append(entry)

    #-----------------------------------------------------------------------
    def to_json(self):
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
