#===========================================================================
#
# Dimmer module
#
#===========================================================================
from .Device import Device
import logging

s_log = logging.getLogger(__name__)

class Remote (Device):
    def __init__(self, address, num, name=None):
        super().__init__(address, name)
        self.num = num
        self._is_on = [None]*num

    #-----------------------------------------------------------------------
    def pair(self, modem):
        s_log.info( "Dimmer %s pairing with modem", self.addr)
        # TODO: pair with modem
        pass

    #-----------------------------------------------------------------------
    def is_on(self, button):
        return not self._is_on[button]

    #-----------------------------------------------------------------------
    def level(self):
        return self._is_on[button]

    #-----------------------------------------------------------------------
    def on(self, button, level=0xFF, instant=False):
        s_log.info( "Remove %s btn: %s cmd: on %s", self.addr, button, level)
        # TODO: on command
        pass

    #-----------------------------------------------------------------------
    def off(self, button, instant=False):
        s_log.info( "Remove %s btn: %s cmd: off %s", self.addr, button, level)
        # TODO: off command
        pass

    #-----------------------------------------------------------------------
    def set(self, active, button, instant=False):
        if active:
            self.on(button, instant)
        else:
            self.off(button, instant)

    #-----------------------------------------------------------------------
    def _update(self):
        # TODO: send status command, update internal state
        pass

    #-----------------------------------------------------------------------
