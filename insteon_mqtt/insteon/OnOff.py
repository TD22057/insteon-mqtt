#===========================================================================
#
# On/off module
#
#===========================================================================
from .Device import Device
from .. import Signal
import logging

s_log = logging.getLogger(__name__)

class OnOff (Device):
    def __init__(self, handler, address, name=None):
        super().__init__(handler, address, name)
        # 0x00 for off or 0xff for on
        self._level = 0x00 

        self.signal_state = Signal.Signal()

    #-----------------------------------------------------------------------
    def pair(self, modem):
        s_log.info( "Dimmer %s pairing with modem", self.addr)
        # TODO: pair with modem
        pass

    #-----------------------------------------------------------------------
    def handle_direct_ack(self, msg):
        self._level = 0xff if msg.cmd2 else 0x00
        self.signal_state.emit(self._level)
        
    #-----------------------------------------------------------------------
    def is_on(self):
        return self._level > 0x00

    #-----------------------------------------------------------------------
    def level(self):
        return self._level

    #-----------------------------------------------------------------------
    def on(self, instant=False):
        s_log.info( "OnOff %s cmd: on", self.addr)

        cmd1 = 0x11 if not instant else 0x21
        msg = Msg.OutStandard.direct(self.addr, cmd1, 0xff)
        self.handler.send(msg, StandardCmdHandler(self, cmd1))

    #-----------------------------------------------------------------------
    def off(self, instant=False):
        s_log.info( "OnOff %s cmd: off", self.addr)

        cmd1 = 0x13 if not instant else 0x21
        msg = Msg.OutStandard.direct(self.addr, cmd1, 0x00)
        self.handler.send(msg, StandardCmdHandler(self, cmd1))

    #-----------------------------------------------------------------------
    def set(self, active, instant=False):
        if active:
            self.on(instant)
        else:
            self.off(instant)

    #-----------------------------------------------------------------------
    def _update(self):
        # TODO: send status command, update internal state
        pass

    #-----------------------------------------------------------------------
