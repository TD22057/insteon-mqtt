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

class OnOff (Base):
    def __init__(self, protocol, modem, address, name=None):
        super().__init__(protocol, modem, address, name)
        # 0x00 for off or 0xff for on
        self._level = 0x00 

        self.signal_level_changed = Signal.Signal()

    #-----------------------------------------------------------------------
    def pair(self):
        LOG.info( "Dimmer %s pairing with modem", self.addr)
        # TODO: pair with modem
        pass

    #-----------------------------------------------------------------------
    def is_on(self):
        return self._level > 0x00

    #-----------------------------------------------------------------------
    def level(self):
        return self._level

    #-----------------------------------------------------------------------
    def on(self, instant=False):
        LOG.info( "OnOff %s cmd: on", self.addr)

        cmd1 = 0x11 if not instant else 0x21
        msg = Msg.OutStandard.direct(self.addr, cmd1, 0xff)
        self.protocol.send(msg, handler.StandardCmd(self, cmd1))

    #-----------------------------------------------------------------------
    def off(self, instant=False):
        LOG.info( "OnOff %s cmd: off", self.addr)

        cmd1 = 0x13 if not instant else 0x21
        msg = Msg.OutStandard.direct(self.addr, cmd1, 0x00)
        self.protocol.send(msg, handler.StandardCmd(self, cmd1))

    #-----------------------------------------------------------------------
    def set(self, active, instant=False):
        if active:
            self.on(instant)
        else:
            self.off(instant)

    #-----------------------------------------------------------------------
    def run_command(self, **kwargs):
        LOG.info("OnOff command: %s", kwargs)
        if 'level' in kwargs:
            level = int(kwargs.pop('level'))
            instant = bool(kwargs.pop('instant', False))
            if level == 0:
                self.off(instant)
            else:
                self.on(instant)

        else:
            Base.run_command(**kwargs)
        
    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        # ACK of the broadcast - ignore this.
        if msg.cmd1 == 0x06:
            LOG.info( "OnOff %s broadcast ACK grp: %s", self.addr, msg.group)
            return

        # On command.  How do we tell the level?  It's not in the
        # message anywhere.
        elif msg.cmd1 == 0x11:
            LOG.info( "OnOff %s broadcast ON grp: %s", self.addr, msg.group)
            self._set_level(0xff)
            
        # Off command.
        elif msg.cmd1 == 0x13:
            LOG.info( "OnOff %s broadcast OFF grp: %s", self.addr, msg.group)
            self._set_level(0x00)
        
        # Call handle_broadcast for any device that we're the
        # controller of.
        Base.handle_broadcast(self, msg)
        
    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        LOG.debug("OnOff %s refresh message: %s", self.addr, msg)

        # Current on/off level is stored in cmd2 so update our level
        # to match.
        self._set_level(0xff if msg.cmd2 else 0x00)

        # See if the database is up to date.
        Base.handle_refresh(self, msg)

    #-----------------------------------------------------------------------
    def handle_ack(self, msg):
        LOG.debug("OnOff %s ack message: %s", self.addr, msg)
        self._set_level(0xff if msg.cmd2 else 0x00)

    #-----------------------------------------------------------------------
    def handle_group_cmd(self, addr, msg):
        entry = self.db.find(addr, msg.group, 'RESP')
        if not entry:
            LOG.error("OnOff %s has no group %s entry from %s", self.addr,
                      msg.group, addr)
            return

        if msg.cmd1 == 0x11:
            self._set_level(entry.on_level)
        else:
            self._set_level(0x00)
        
    #-----------------------------------------------------------------------
    def _set_level(self, level):
        LOG.info("Setting device %s '%s' level %s", self.addr, self.name, level)
        self._level = 0x00 if not level else 0xff
        self.signal_level_changed.emit(self, self._level)
        
    #-----------------------------------------------------------------------
