#===========================================================================
#
# SmokeBridge module
#
#===========================================================================
from .Base import Base
from .. import Signal
import logging

LOG = logging.getLogger(__name__)

class SmokeBridge (Base):
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
        LOG.debug("Dimmer %s ack message: %s", self.addr,msg)
        if msg.flags.type == Msg.Flags.DIRECT_ACK:
            self._set_level(msg.cmd2)

    #-----------------------------------------------------------------------
    def run_command(self, **kwargs):
        LOG.info("Dimmer command: %s", kwargs)
        if 'level' in kwargs:
            level = int(kwargs.pop('level'))
            instant = bool(kwargs.pop('instant', False))
            if level == 0:
                self.off(instant)
            else:
                self.on(level, instant)

        elif 'increment' in kwargs:
            dir = kwargs.pop('increment')
            if dir == +1:
                self.incrementUp()
            elif dir == -1:
                self.incrementDown()
            else:
                LOG.error("Invalid increment %s", dir)

        elif 'getdb' in kwargs:
            self.get_db()

        elif 'refresh' in kwargs:
            self.refresh()
            
        else:
            LOG.error("Invalid commands to dimmer")
        
    #-----------------------------------------------------------------------
