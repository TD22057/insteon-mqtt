#===========================================================================
#
# Insteon PLM modem all link database entry
#
#===========================================================================
import logging
from ..Address import Address

LOG = logging.getLogger(__name__)


class ModemEntry:
    @staticmethod
    def from_json(data):
        return ModemEntry(Address.from_json(data['addr']),
                          data['group'],
                          data['is_controller'],
                          bytes(data['data']))

    #-----------------------------------------------------------------------
    def __init__(self, addr, group, is_controller, data):
        self.addr = addr
        self.group = group
        self.is_controller = is_controller
        self.is_responder = not is_controller
        self.data = data
        self.on_level = data[0]
        self.ramp_rate = data[1]

    #-----------------------------------------------------------------------
    def to_json(self):
        return {
            'addr' : self.addr.to_json(),
            'group' : self.group,
            'is_controller' : self.is_controller,
            'data' : list(self.data)
            }

    #-----------------------------------------------------------------------
    def __eq__(self, rhs):
        return (self.addr.id == rhs.addr.id and
                self.group == rhs.group and
                self.is_controller == rhs.is_controller)

    #-----------------------------------------------------------------------
    def __str__(self):
        return "ID: %s  grp: %s  type: %s  data: %#04x %#04x %#04x" % \
            (self.addr.hex, self.group, 'CTRL' if self.is_controller else 'RESP',
             self.data[0], self.data[1], self.data[2])

    #-----------------------------------------------------------------------
