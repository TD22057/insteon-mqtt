#===========================================================================
#
# Insteon modem
#
#===========================================================================
from .Address import Address
from . import config
from ..Signal import Signal
import logging
import os
from . import msg as Msg

class ModemDbHandler:
    def __init__(self, modem):
        self.modem = modem
        
    def msg_received(self, handler, msg):
        # Message is an ACK/NAK of the record request.
        if (isinstance(msg, Msg.OutAllLinkGetFirst) or
            isinstance(msg, Msg.OutAllLinkGetNext)):
            # If we get a NAK, then there are no more db records.
            if not msg.is_ack:
                self.modem.log.info("Modem finished - last db record received")
                self.modem._get_db_finished()
                return Msg.FINISHED

            # ACK - keep reading until we get the record we requested.
            return Msg.CONTINUE

        # Message is the record we requested.
        if isinstance(msg, Msg.InpAllLinkRec):
            self.modem.log.info("Modem db record received")
            self.modem.add_db_rec(msg)

            # Request the next record in the PLM database.
            self.modem.log.info("Modem requesting next db record")
            msg = Msg.OutAllLinkGetNext()
            handler.send(msg, self)
            return Msg.CONTINUE

        return Msg.UNKNOWN
        
class BroadcastHandler:
    def __init__(self, modem):
        self.modem = modem
        self.log = logging.getLogger(__name__)
        
    def msg_received(self, handler, msg):
        if not isinstance(msg, Msg.InpStandard):
            return Msg.UNKNOWN

        if msg.flags.type == Msg.Flags.ALL_LINK_BROADCAST:
            try:
                device = self.modem.find(msg.from_addr)
            except:
                self.log.error("Unknown broadcast device %s", msg.from_addr)
                return Msg.UNKNOWN

            self.log.info("Handling all link broadcast for %s '%s'",
                          device.addr, device.name)
            device.handle_broadcast(msg)
            return Msg.FINISHED
            
        elif msg.flags.type == Msg.Flags.ALL_LINK_CLEANUP:
            self.log.info("Ignoring broadcast clean up")
            # TODO: what to do with this?

        return Msg.UNKNOWN


#===========================================================================
class Modem:
    def __init__(self, handler, db_path=None):
        self.handler = handler # TODO: fix naming -> Protocol/Transport/Link
        self.addr = None
        self.db_path = db_path # TODO: fix naming
        self.devices = {}
        self.scenes = {}
        self.db = [] # TODO

        self.log = logging.getLogger(__name__)

        self.handler.add_handler(BroadcastHandler(self))

        self.signal_new_device = Signal() # emit(modem, device)

    #-----------------------------------------------------------------------
    def load_config(self, data):
        self.log.info("Loading configuration data")
        
        self.handler.load_config(data)
        
        self.addr = Address(data['address'])
        self.log.info("Modem address set to %s", self.addr)
        
        self.devices = self._load_devices(data.get('devices', []))
        
        self.scenes = self._load_scenes(data.get('scenes', []))
        if 'storage' in data:
            self.db_path = data['storage']

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        # TODO: what should modem do?
        pass
        
    #-----------------------------------------------------------------------
    def get_db(self):
        self.log.info("Modem sending get first db record command")
        
        # Request the first db record from the handler.  The handler
        # will request each next record as the records arrive.
        msg = Msg.OutAllLinkGetFirst()
        msg_handler = ModemDbHandler(self)
        self.handler.send(msg, msg_handler)
        
    #-----------------------------------------------------------------------
    def _get_db_finished(self):
        print("============")
        for rec in self.db:
            print(rec)
        print("============")

    #-----------------------------------------------------------------------
    def add_db_rec(self, msg):
        assert(isinstance(msg, Msg.InpAllLinkRec))
        if not msg.ctrl.in_use:
            self.log.info("Ignoring modem db record in_use = False")
            return
        
        self.log.info("Adding modem db record for %s grp: %s",
                      msg.addr, msg.group)
        # TODO: save in db
        self.db.append(msg)
        
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
    def run_command(self, **kwargs):
        self.log.info("Modem command: %s", kwargs)
        if 'getdb' in kwargs:
            self.get_db()
        else:
            self.log.error("Invalid command sent to modem %s", kwargs)
            
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
            d = ctor(**args, handler=self.handler)
            self.log.info("Created %s at %s '%s'", d.__class__.__name__,
                          d.addr, d.name)
            
            # Load an existing database for this device if it exists.
            if self.db_path:
                db_path = os.path.join(self.db_path, d.addr.hex)
                if os.path.exists(db_path):
                    d.load_db_file(db_path)

            devices[d.addr.id] = d
            self.signal_new_device.emit(self, d)

        return devices

    #-----------------------------------------------------------------------
    def _load_scenes(self, data):
        scenes = {}
        return scenes

    #-----------------------------------------------------------------------
