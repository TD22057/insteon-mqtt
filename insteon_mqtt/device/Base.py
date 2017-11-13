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
        self._next_db_delta = None

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

        LOG.info("Device %s database saved %s entries", self.addr,
                 len(self.db))

    #-----------------------------------------------------------------------
    def load_db(self, path):
        try:
            with open(path) as f:
                data = json.load(f)
        except:
            LOG.exception("Error reading file %s", path)
            return

        self.db = db.Device.from_json(data)

        LOG.info("Device %s database loaded %s entries", self.addr,
                 len(self.db))
        LOG.debug(str(self.db))
                     
    #-----------------------------------------------------------------------
    def get_db(self, db_delta):
        LOG.info("Device %s sending get first db record command",
                 self.addr)

        self.db.clear()
        self._next_db_delta = db_delta
        
        # Request that the device send us all of it's database
        # records.  These will be streamed as fast as possible to us.
        msg = Msg.OutExtended.direct(self.addr, 0x2f, 0x00, bytes(14))
        msg_handler = handler.DeviceDb(self.addr, self.handle_db_rec)
        self.protocol.send(msg, msg_handler)
        
    #-----------------------------------------------------------------------
    def run_command(self, **kwargs):
        if 'getdb' in kwargs:
            # We need to get the current db delta so we know which one
            # we're getting.  So clear the current flag and then do a
            # refresh which will find the delta and then trigger a
            # download.
            self.db.clear_delta()
            self.refresh()

        elif 'refresh' in kwargs:
            self.refresh()
            
        else:
            LOG.error("Device %s invalid command: %s", self.addr, str(kwargs))
        
    #-----------------------------------------------------------------------
    def refresh(self):
        LOG.info( "Device %s cmd: status refresh", self.addr)

        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x00)

        # The returned message command will be a data field so in this
        # case don't check it against our input when matching messages.
        msg_handler = handler.StandardCmd(msg, self.handle_refresh, cmd=-1)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        # NOTE: sub classes should probably override this and call
        # this as well when done.
        # All link database delta is stored in cmd1 so we if we have
        # the latest version.  If not, schedule an update.
        if not self.db.is_current(msg.cmd1):
            LOG.info("Device %s db out of date - refreshing", self.addr)
            self.get_db(msg.cmd1)
        
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
            else:
                LOG.warning("%s broadcast to %s - device %s not found",
                            self.addr, elem.addr)

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
            self.db.delta = self._next_db_delta
            self._next_db_delta = None
            
            LOG.info("%s database download complete\n%s", self.addr, self.db)
            self.save_db()
        
    #-----------------------------------------------------------------------
