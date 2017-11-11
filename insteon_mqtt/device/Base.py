#===========================================================================
#
# Base device class
#
#===========================================================================
import json
import logging
from ..Address import Address
from .. import db
from .. import handler
from .. import message as Msg

LOG = logging.getLogger(__name__)

class Base:
    """Base class for all Insteon devices.
    """
    def __init__(self, protocol, modem, address, name):
        """Constructor

        Args:
           protocol:    (Protocol) The Protocol object used to communicate
                        with the Insteon network.  This is needed to allow
                        the device to send messages to the PLM modem.
           address:     (Address) The address of the device.
           name         (str) Nice alias name to use for the device.
        """
        self.protocol = protocol
        self.modem = modem
        self.addr = Address(address)
        self.name = name
        self.db = db.Device()

    #-----------------------------------------------------------------------
    def ping(self):
        # TODO: send ping command
        pass

    #-----------------------------------------------------------------------
    def db_path(self):
        return self.addr.hex + ".json"
    
    #-----------------------------------------------------------------------
    def save_db(self):
        # TODO: where?
        #if not self.save_path:
        #    return
        data = self.db.to_json()

        with open(self.db_path(), "w") as f:
            json.dump(data, f, indent=2)

        LOG.info("%s database saved %s entries", self.addr, len(self.db))

    #-----------------------------------------------------------------------
    def load_db(self, path):
        try:
            with open(path) as f:
                data = json.load(f)
        except:
            LOG.exception("Error reading file %s", path)
            return

        self.db = db.Device.from_json(data)

        LOG.info("%s database loaded %s entries", self.addr, len(self.db))
        LOG.debug(str(self.db))
                     
    #-----------------------------------------------------------------------
    def get_db(self):
        LOG.info("Device sending get first db record command")
        
        # Request that the device send us all of it's database
        # records.  These will be streamed as fast as possible to us.
        msg = Msg.OutExtended.direct(self.addr, 0x2f, 0x00, bytes(14))
        msg_handler = handler.DeviceDb(self.addr, self.handle_db_rec)
        self.protocol.send(msg, msg_handler)
        
    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        responders = self.db.find_group(msg.group)
        LOG.debug("Found %s responders in group %s", len(responders), msg.group)
        LOG.debug("Group %s -> %s", msg.group, [i.addr.hex for i in responders])
        
        # For each device that we're the controller of call it's
        # handler for the broadcast message.
        for elem in responders:
            device = self.modem.find(elem.addr)
            if device:
                LOG.info("%s broadcast to %s for group %s", self.addr,
                         device.addr, msg.group)
                device.handle_group_cmd(self.addr, msg)

    #-----------------------------------------------------------------------
    def handle_group_cmd(self, addr, msg):
        LOG.info("Device %s ignoring group cmd - not implemented", self.addr)

    #-----------------------------------------------------------------------
    def handle_db_rec(self, msg):
        # New record - add it to the device database.
        if msg is not None:
            self.db.add(msg)
            
        # Finished - we have all the records.
        else:
            # TODO: do something here?
            print("============")
            print(self.db)
            print("============")
            self.save_db()
        
    #-----------------------------------------------------------------------
