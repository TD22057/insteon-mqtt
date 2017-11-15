#===========================================================================
#
# On/off module
#
#===========================================================================
import logging
from .Base import Base
from ..Address import Address
from .. import handler
from .. import message as Msg
from .. import Signal

LOG = logging.getLogger(__name__)

class Motion (Base):
    def __init__(self, protocol, modem, address, name=None):
        super().__init__(protocol, modem, address, name)
        self._is_on = False
        self._saved_broadcast = None

        self.signal_active = Signal.Signal()  # (device, bool)

    #-----------------------------------------------------------------------
    def pair(self):
        LOG.info( "Dimmer %s pairing with modem", self.addr)
        # TODO: pair with modem
        pass

    #-----------------------------------------------------------------------
    def is_on(self):
        return self._is_on

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        LOG.debug( "Motion %s broadcast", self.addr)
        
        # ACK of the broadcast - ignore this.
        if msg.cmd1 == 0x06:
            LOG.info( "Motion %s broadcast ACK grp: %s", self.addr, msg.group)
            return

        # On command.  
        elif msg.cmd1 == 0x11:
            LOG.info( "Motion %s broadcast ON grp: %s", self.addr, msg.group)
            self._set_is_on(True)
            
        # Off command.
        elif msg.cmd1 == 0x13:
            LOG.info( "Motion %s broadcast OFF grp: %s", self.addr, msg.group)
            self._set_is_on(False)

        # If we have the device database, broadcast to the devices
        # we're linked to.
        if len(self.db):
            LOG.debug( "Motion %s have db %s", self.addr, len(self.db))

            # Call handle_broadcast for any device that we're the
            # controller of.
            Base.handle_broadcast(self, msg)

        # Otherwise, use this opportunity to get the device db since
        # we know the sensor is awake.
        else:
            # This isn't working - maybe need to wait for all the
            # broadcast messages to arrive?
            pass
            #LOG.info("Motion %s awake - requesting database", self.addr)
            #self._saved_broadcast = msg
            #self.get_db(db_delta=0)
            #self.refresh()
        
    #-----------------------------------------------------------------------
    def handle_db_rec(self, msg):
        Base.handle_db_rec(self, msg)
        
        if msg is None and self._saved_broadcast:
            Base.handle_broadcast(self, self._saved_broadcast)
            self._saved_broadcast = None
            
    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        LOG.debug("Motion %s refresh message: %s", self.addr, msg)

        # Current on/off level is stored in cmd2 so update our level
        # to match.
        self._set_is_on(msg.cmd2 != 0x00)

        # See if the database is up to date.
        Base.handle_refresh(self, msg)

    #-----------------------------------------------------------------------
    def handle_ack(self, msg):
        LOG.debug("Motion %s ack message: %s", self.addr, msg)
        self._set_level(msg.cmd2 != 0x00)

    #-----------------------------------------------------------------------
    def _set_is_on(self, is_on):
        LOG.info("Setting device %s '%s' on %s", self.addr, self.name, is_on)
        self._is_on = is_on
        self.signal_active.emit(self, self._is_on)
        
    #-----------------------------------------------------------------------
