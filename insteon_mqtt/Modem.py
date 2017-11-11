#===========================================================================
#
# Insteon modem
#
#===========================================================================
import json
import logging
import os
from . import db
from . import config
from .Address import Address
from . import handler
from . import message as Msg
from .Signal import Signal

LOG = logging.getLogger(__name__)

#===========================================================================
class Modem:
    def __init__(self, protocol):
        self.protocol = protocol
        self.addr = None
        self.save_path = None
        self.devices = {}
        self.scenes = {}
        self.db = db.Modem()

        self.signal_new_device = Signal() # emit(modem, device)

        self.protocol.add_handler(handler.Broadcast(self))

    #-----------------------------------------------------------------------
    def load_config(self, data):
        LOG.info("Loading configuration data")
        
        self.protocol.load_config(data)
        
        self.addr = Address(data['address'])
        LOG.info("Modem address set to %s", self.addr)
        
        if 'storage' in data:
            self.save_path = data['storage']
            self.load_db()
            
        self.devices = self._load_devices(data.get('devices', []))
        self.scenes = self._load_scenes(data.get('scenes', []))

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        # TODO: what should modem do?
        pass
        
    #-----------------------------------------------------------------------
    def handle_group_cmd(self, addr, msg):
        pass
        
    #-----------------------------------------------------------------------
    def get_db(self):
        LOG.info("Modem sending get first db record command")
        
        # Request the first db record from the handler.  The handler
        # will request each next record as the records arrive.
        msg = Msg.OutAllLinkGetFirst()
        msg_handler = handler.ModemDb(self)
        self.protocol.send(msg, msg_handler)
        
    #-----------------------------------------------------------------------
    def db_path(self):
        return os.path.join(self.save_path, self.addr.hex) + ".json"
        
    #-----------------------------------------------------------------------
    def save_db(self):
        if not self.save_path:
            return
        
        data = self.db.to_json()

        with open(self.db_path(), "w") as f:
            json.dump(data, f, indent=2)

        LOG.info("%s database saved %s entries", self.addr, len(self.db))

    #-----------------------------------------------------------------------
    def load_db(self):
        path = self.db_path()
        if not os.path.exists(path):
            return
        
        try:
            with open(path) as f:
                data = json.load(f)
        except:
            LOG.exception("Error reading file %s", path)
            return

        self.db = db.Modem.from_json(data)

        LOG.info("%s database loaded %s entries", self.addr, len(self.db))
                     
    #-----------------------------------------------------------------------
    def handle_db_rec(self, msg):
        if msg is None:
            # TODO: do something here?
            print("============")
            print(self.db)
            print("============")
            self.save_db()
        else:
            assert(isinstance(msg, Msg.InpAllLinkRec))
            if not msg.flags.in_use:
                LOG.info("Ignoring modem db record in_use = False")
                return

            self.db.add(msg)
        
    #-----------------------------------------------------------------------
    def add(self, device):
        self.devices[device.addr.id] = device
        # db files?

    #-----------------------------------------------------------------------
    def remove(self, device):
        del devices[device.addr.id]
        # db files?

    #-----------------------------------------------------------------------
    def find(self, addr):
        if not isinstance(addr, Address):
            addr = Address(addr)

        if addr == self.addr:
            return self
        
        device = self.devices.get(addr.id, None)
        if device:
            return device
        
        return None

    #-----------------------------------------------------------------------
    def reload_all(self):
        pass

    #-----------------------------------------------------------------------
    def run_command(self, **kwargs):
        LOG.info("Modem command: %s", kwargs)
        # TODO: modem broadcast group command
        if 'getdb' in kwargs:
            self.get_db()
        else:
            LOG.error("Invalid command sent to modem %s", kwargs)
            
    #-----------------------------------------------------------------------
    def _load_devices(self, data):
        """
        [{'on_off': {'address': 'a2.b3.c4', 'name': 'lamp'}},
             {'dimmer': {'address': 'a2.b3.c4', 'name': 'hallway'}},
             {'smoke_bridge': {'address': 'a2.b3.c4'}},
             {'remote8': {'address': 'a2.b3.c4', 'name': 'remote_01'}}],
        """
        device_map = {}
        for entry in data:
            assert(len(entry) == 1)

            type = next(iter(entry))
            ctor = config.find(type)

            args = entry[type]
            device = ctor(**args, protocol=self.protocol, modem=self)
            LOG.info("Created %s at %s '%s'", device.__class__.__name__,
                     device.addr, device.name)
            
            # Load an existing database for this device if it exists.
            if self.save_path:
                save_path = os.path.join(self.save_path,
                                         device.addr.hex) + ".json"
                if os.path.exists(save_path):
                    LOG.info("%s loading device db %s",device.addr, save_path)
                    device.load_db(save_path)

            device_map[device.addr.id] = device
            self.signal_new_device.emit(self, device)

        return device_map

    #-----------------------------------------------------------------------
    def _load_scenes(self, data):
        scenes = {}
        return scenes

    #-----------------------------------------------------------------------
