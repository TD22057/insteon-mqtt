#===========================================================================
#
# Device all link database
#
#===========================================================================
from .Address import Address
from . import msg as Msg
import logging
import io

#===========================================================================

# Database fields:
# PLM Modem DB:
#    DbFlags, device_addr, group, data[3]
#
# Device Db:
#    DbFlags, device_addr, group, data[3], rec_memory[2]
#
# Managing records:
# PLM Modem:
#    direct commands (0x6f->OutAllLinkUpdate) to add/del/edit records
#
# Devices:
#    memory edits using OutExtended cmd=0x2f
#    needs to know current memory layout and update accordingly
#
# Design questions:
# What is db needed for?
#   1) respond to all link commands received from modem
#      find linked devices, send command to them
#      probably cache this or create when db is loaded
#   2) load/reload db
#      need to go get db, store it, save it locally, reload it locally
#   3) link devices to modem
#      needed to add new devices.  Create modem link, create link in device
#   4) create scenes
#      adding new links and pushing to devices and modem
#      >>most complicated, also needs scene classes

class LinkDb:
    def __init__(self, addr):
        assert(isinstance(addr, Address))
        
        self.addr = addr
        self.entries = []

        # Map this device's group number to addresses of other devices
        # in the group.  This is group of devices for which this db is
        # the controller and those devices are the responders.  When
        # we see a message saying this device sent an all link command
        # to this group, we can use this dict to quickly find all the
        # devices in the group.
        self.groups = {}

    #-----------------------------------------------------------------------
    def group(self, id):
        if not self.groups:
            self._build_groups()
            
        devices = self.groups.get(id, [])
        return devices
            
    #-----------------------------------------------------------------------
    def _build_groups(self):
        self.groups = {}
        for e in self.entries:
            if e.flags.is_controller:
                devices = self.groups.get(e.group, [])
                devices.append(e.addr)
            
    #-----------------------------------------------------------------------
    def add(self, msg):
        assert(isinstance(msg, Msg.InpAllLinkRec))
        for e in entries:
            if e == msg:
                continue
            
        self.flags = msg.flags
        self.group = msg.group
        self.addr = msg.addr
        self.data = msg.data
        
    #-----------------------------------------------------------------------
    def save(self, f):
        for e in self.entries:
            f.write(e.to_json())

    #-----------------------------------------------------------------------
    def load(self, f):
        data = json.load(f)
        for d in data:
            self.entries.append(DbEntry.from_json(d))

    
#===========================================================================
