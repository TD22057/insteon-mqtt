#===========================================================================
#
# Non-modem device all link database class
#
#===========================================================================
import logging
from ..Address import Address
from .. import message as Msg

LOG = logging.getLogger(__name__)


#===========================================================================
class DeviceEntry:
    @staticmethod
    def from_json(data):
        return DeviceEntry(Address.from_json(data['addr']),
                           data['group'],
                           data['mem_loc'],
                           Msg.DbFlags.from_json(data['ctrl']),
                           bytes(data['data']))
    
    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(data):
        # See p162 of insteon dev guide
        # [0] = unused
        # [1] = request/response flag
        mem_loc = (data[2] << 8) + data[3]
        # [4] = dump request flag
        ctrl = Msg.DbFlags.from_bytes(data, 5)
        group = data[6]
        link_addr = Address.from_bytes(data, 7)
        on_level = data[10]
        ramp_rate = data[11]
        link_data = data[10:13]

        return DeviceEntry(link_addr, group, mem_loc, ctrl, link_data)

    #-----------------------------------------------------------------------
    def __init__(self, addr, group, mem_loc, ctrl, data):
        self.addr = addr
        self.group = group
        self.mem_loc = mem_loc
        self.ctrl = ctrl
        self.data = data
        self.on_level = data[0]
        self.ramp_rate = data[1]

    #-----------------------------------------------------------------------
    def mem_bytes(self):
        high = (self.mem_loc & 0xFF00) >> 8
        low =  (self.mem_loc & 0x00FF) >> 0
        return bytes([high, low])
    
    #-----------------------------------------------------------------------
    def to_json(self):
        return {
            'addr' : self.addr.to_json(),
            'group' : self.group,
            'mem_loc' : self.mem_loc,
            'ctrl' : self.ctrl.to_json(),
            'data' : list(self.data)
            }
        
    #-----------------------------------------------------------------------
    def __eq__(self, rhs):
        return (self.addr.id == rhs.addr.id and
                self.group == rhs.group and
                self.ctrl.is_controller == rhs.ctrl.is_controller)
    
    #-----------------------------------------------------------------------
    def __str__(self):
        return "ID: %s  grp: %s  type: %s  data: %#04x %#04x %#04x" % \
            (self.addr.hex, self.group,
             'CTRL' if self.ctrl.is_controller else 'RESP',
             self.data[0], self.data[1], self.data[2])
    
    #-----------------------------------------------------------------------

