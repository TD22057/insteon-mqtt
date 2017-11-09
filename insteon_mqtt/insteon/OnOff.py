#===========================================================================
#
# On/off module
#
#===========================================================================
from .Device import Device
from .. import sigslot
import logging

s_log = logging.getLogger(__name__)

class OnOff (Device):
    def __init__(self, address, name=None):
        super().__init__(address, name)
        self._is_on = None

        self.signal_state = sigslot.Signal()

    #-----------------------------------------------------------------------
    def pair(self, modem):
        s_log.info( "Dimmer %s pairing with modem", self.addr)
        # TODO: pair with modem
        pass

    #-----------------------------------------------------------------------
    def is_on(self):
        return self._is_on

    #-----------------------------------------------------------------------
    def level(self):
        return 0xFF if self._is_on else 0

    #-----------------------------------------------------------------------
    def on(self, instant=False):
        s_log.info( "OnOff %s cmd: on", self.addr)
        assert(level >= 0 and level <= 0xff)
        
        if not instant:
            msg = Msg.OutStandard.direct(self.addr, 0x11, level)
        else:
            msg = Msg.OutStandard.direct(self.addr, 0x21, level)

    #-----------------------------------------------------------------------
    def off(self, instant=False):
        s_log.info( "OnOff %s cmd: off", self.addr)

        if not instant:
            msg = Msg.OutStandard.direct(self.addr, 0x13, 0x00)
        else:
            msg = Msg.OutStandard.direct(self.addr, 0x21, 0x00)

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
