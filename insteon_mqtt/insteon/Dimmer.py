#===========================================================================
#
# Dimmer module
#
#===========================================================================
from .Device import Device
from .. import sigslot
import logging

s_log = logging.getLogger(__name__)

class Dimmer (Device):
    def __init__(self, address, name=None):
        super().__init__(address, name)
        self._level = None

        self.signal_state = sigslot.Signal()

    #-----------------------------------------------------------------------
    def pair(self, modem):
        s_log.info( "Dimmer %s pairing with modem", self.addr)
        # TODO: pair with modem
        pass

    #-----------------------------------------------------------------------
    def is_on(self):
        return not self._level

    #-----------------------------------------------------------------------
    def level(self):
        return self._level

    #-----------------------------------------------------------------------
    def on(self, level=0xFF, instant=False):
        s_log.info( "Dimmer %s cmd: on %s", self.addr, level)
        assert(level >= 0 and level <= 0xff)
        
        if not instant:
            msg = Msg.OutStandard.direct(self.addr, 0x11, level)
        else:
            msg = Msg.OutStandard.direct(self.addr, 0x21, level)

    #-----------------------------------------------------------------------
    def off(self, instant=False):
        s_log.info( "Dimmer %s cmd: off", self.addr)

        if not instant:
            msg = Msg.OutStandard.direct(self.addr, 0x13, 0x00)
        else:
            msg = Msg.OutStandard.direct(self.addr, 0x21, 0x00)

    #-----------------------------------------------------------------------
    def incrementUp(self):
        s_log.info( "Dimmer %s cmd: increment up", self.addr)
        msg = Msg.OutStandard.direct(self.addr, 0x15, 0x00)

    #-----------------------------------------------------------------------
    def incrementDown(self):
        s_log.info( "Dimmer %s cmd: increment down", self.addr)
        msg = Msg.OutStandard.direct(self.addr, 0x16, 0x00)

    #-----------------------------------------------------------------------
    def manualStartUp(self):
        s_log.info( "Dimmer %s cmd: manual start up", self.addr)
        msg = Msg.OutStandard.direct(self.addr, 0x17, 0x01)

    #-----------------------------------------------------------------------
    def manualStartDown(self):
        s_log.info( "Dimmer %s cmd: manual start down", self.addr)
        msg = Msg.OutStandard.direct(self.addr, 0x17, 0x00)

    #-----------------------------------------------------------------------
    def manualStop(self):
        s_log.info( "Dimmer %s cmd: manual stop", self.addr)
        msg = Msg.OutStandard.direct(self.addr, 0x18, 0x00)

    #-----------------------------------------------------------------------
    def set(self, active, level=0xFF, instant=False):
        if active:
            self.on(level, instant)
        else:
            self.off(instant)

    #-----------------------------------------------------------------------
    def process_message(self, msg):
        assert(msg.addr == self.addr)

        if isinstance(msg, Msg.OutStandard):
            if msg.flags.is_nak:
                # TODO: what to do?
                return

            new_level = self._level
            if msg.type == Msg.Flags.DIRECT:
                if msg.cmd1 == 0x11:
                    new_level = msg.cmd2
                elif msg.cmd1 == 0x13:
                    new_level = 0

            elif msg.is_broadcast:
                # For BROADCAST , CLEANUP, or ?CLEANUP_ACK?
                
                # get group number, look up RESPONDER field in db for
                # modem and get level from all link database record.
                pass
            
            if new_level != self._level:
                self._level = new_level
                self.signal_state.emit(self._level)
        
    #-----------------------------------------------------------------------
    def run_command(self, **kwargs):
        s_log.info("Dimmer command: %s", kwargs)
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
                s_log.error("Invalid increment %s", dir)

        else:
            s_log.error("Invalid commands to dimmer")
        
    #-----------------------------------------------------------------------
    def _update(self):
        # TODO: send status command, update internal state
        pass

    #-----------------------------------------------------------------------
