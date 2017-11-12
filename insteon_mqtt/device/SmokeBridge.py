#===========================================================================
#
# SmokeBridge module
#
#===========================================================================
from .Base import Base
from .. import message as Msg
from .. import handler
from .. import Signal
import logging

LOG = logging.getLogger(__name__)

class SmokeBridge (Base):
    """

    NOTE: no way to read current alarm condition.  If the message is
    sent and we don't get it - there is no way to retreive it.
    """
    conditions = {
        0x01 : 'smoke',
        0x02 : 'CO',
        0x03 : 'test',
        0x05 : 'clear',
        0x06 : 'low battery',
        0x07 : 'error',
        0x0a : 'heartbeat',
        }
        
    def __init__(self, protocol, modem, address, name=None):
        super().__init__(protocol, modem, address, name)

        # emit(device, condition)
        self.signal_state_change = Signal.Signal()
        
        
    #-----------------------------------------------------------------------
    def pair(self):
        LOG.info( "Smoke bridge %s pairing with modem", self.addr)
        # TODO: pair with modem
        pass

    #-----------------------------------------------------------------------
    def refresh(self):
        LOG.info( "Smoke bridge %s cmd: status refresh", self.addr)

        # There is no way to get the current device status but we can
        # request the all link database delta so get that.  See smoke
        # bridge dev guide p25.
        msg = Msg.OutStandard.direct(self.addr, 0x1f, 0x01)

        # The returned message command will put the database delta in cmd2.
        msg_handler = handler.StandardCmd(msg, self.handle_refresh)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        # See we if we have the latest version of the all link
        # database.  If not, schedule an update.
        if not self.db.is_current(msg.cmd2):
            LOG.info("Smoke bridge %s db out of date - refreshing",
                     self.addr)
            self.get_db(msg.cmd2)
        
    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        LOG.debug("Smoke bridge %s refresh message: %s", self.addr, msg)
        Base.handle_refresh(self, msg)
            
    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        # ACK of the broadcast - ignore this.
        if msg.cmd1 == 0x06:
            LOG.info( "Smoke bridge %s broadcast ACK grp: %s", self.addr,
                      msg.group)
            return

        # 0x11 ON command for the smoke bridge means the error is active.
        elif msg.cmd1 == 0x11:
            LOG.info( "Smoke bridge %s broadcast ON grp: %s", self.addr,
                      msg.group)

            condition = self.conditions.get(msg.group, None)
            if condition:
                LOG.info( "Smoke bridge %s signaling group %s", self.addr,
                          msg.group)
                self.signal_state_change.emit(self, condition)
            else:
                LOG.info( "Smoke bridge %s ignoring group %s", self.addr,
                          msg.group)
            

        # Call handle_broadcast for any device that we're the
        # controller of.
        Base.handle_broadcast(self, msg)
        
    #-----------------------------------------------------------------------
    def handle_ack(self, msg):
        LOG.debug("Smoke bridge %s ack message: %s", self.addr, msg)
        if msg.flags.type == Msg.Flags.DIRECT_ACK:
            self._set_level(msg.cmd2)

    #-----------------------------------------------------------------------
    def run_command(self, **kwargs):
        LOG.info("Smoke bridge %s command: %s", self.addr, kwargs)
        Base.run_command(self, **kwargs)
        
    #-----------------------------------------------------------------------
