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
        for d in data:
            entry = ModemEntry.from_json(d)
            obj.add_entry(entry)

        return obj

    #-----------------------------------------------------------------------
    def __init__(self):
        self.entries = {}
        self.num = 0

    #-----------------------------------------------------------------------
    def __len__(self):
        return self.num
        
    #-----------------------------------------------------------------------
    def add(self, msg):
        assert(isinstance(msg, Msg.InpAllLinkRec))
        LOG.info("Adding modem db record for %s grp: %s", msg.addr, msg.group)

        entry = ModemEntry(msg.addr, msg.group, msg.flags.is_controller,
                           msg.data)
        self.add_entry(entry)

    #-----------------------------------------------------------------------
    def add_entry(self, entry):
        assert(isinstance(entry, ModemEntry))
        
        elems = self.entries.setdefault(entry.addr.id, [])
        try:
            idx = elems.index(entry)
            elems[idx].update(entry)
        except ValueError:
            elems.append(entry)
            self.num += 1

    #-----------------------------------------------------------------------
    def to_json(self):
        data = []
        for elems in self.entries.values():
            for entry in elems:
                data.append( entry.to_json() )

        return data

    #-----------------------------------------------------------------------
    def __str__(self):
        o = io.StringIO()
        o.write("ModemDb:\n")
        for id in sorted(self.entries.keys()):
            for elem in self.entries[id]:
                o.write("  %s\n" % elem)
                
        return o.getvalue()

#===========================================================================
