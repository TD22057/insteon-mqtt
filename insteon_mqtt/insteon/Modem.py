#===========================================================================
#
# Insteon modem
#
#===========================================================================
from .Address import Address
from . import config
import os

class Modem:
    def __init__(self, handler, db_path=None):
        self.handler = handler
        self.addr = None
        self.db_path = db_path
        self.devices = {}
        self.scenes = {}

    #-----------------------------------------------------------------------
    def load_config(self, data):
        self.handler.load_config(data)
        
        self.addr = Address(data['address'])
        self.devices = self._load_devices(data.get('devices', []))
        
        self.scenes = self._load_scenes(data.get('scenes', []))
        if 'storage' in data:
            self.db_path = data['storage']

    #-----------------------------------------------------------------------
    def add(self, device):
        self.devices[device.addr.id] = device
        # db files?

    #-----------------------------------------------------------------------
    def remove(self, device):
        del devices[device.addr.id]
        # db files?

    #-----------------------------------------------------------------------
    def find(self, address):
        addr = Address(address)

        device = self.devices.get(addr.id, None)
        if not device:
            if addr == self.addr:
                return self
            
            raise Exception("Requested Insteon device {} doesn't exist in "
                            "the modem database.".format(address))

        return device

    #-----------------------------------------------------------------------
    def reload_all(self):
        pass

    #-----------------------------------------------------------------------
    def _load_devices(self, data):
        """
        [{'on_off': {'address': 'a2.b3.c4', 'name': 'lamp'}},
             {'dimmer': {'address': 'a2.b3.c4', 'name': 'hallway'}},
             {'smoke_bridge': {'address': 'a2.b3.c4'}},
             {'remote8': {'address': 'a2.b3.c4', 'name': 'remote_01'}}],
        """
        devices = {}
        for entry in data:
            assert(len(entry) == 1)

            type = next(iter(entry))
            ctor = config.find(type)

            args = entry[type]
            d = ctor(**args)
            
            # Load an existing database for this device if it exists.
            if self.db_path:
                db_path = os.path.join(self.db_path, d.addr.hex)
                if os.path.exists(db_path):
                    d.load_db_file(db_path)

            devices[d.addr.id] = d

        return devices

    #-----------------------------------------------------------------------
    def _load_scenes(self, data):
        scenes = {}
        return scenes

    #-----------------------------------------------------------------------
