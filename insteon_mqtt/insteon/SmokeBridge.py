#===========================================================================
#
# SmokeBridge module
#
#===========================================================================
from .Device import Device
from .. import sigslot
import logging

s_log = logging.getLogger(__name__)

class SmokeBridge (Device):
    def __init__(self, address, name=None):
        super().__init__(address, name)

        self.signal_smoke = sigslot.Signal()
        self.signal_co = sigslot.Signal()
        self.signal_test = sigslot.Signal()
        self.signal_battery = sigslot.Signal()
        self.signal_error = sigslot.Signal()
        self.signal_heartbeat = sigslot.Signal()

    #-----------------------------------------------------------------------
    def pair(self, modem):
        s_log.info( "Dimmer %s pairing with modem", self.addr)
        # TODO: pair with modem
        pass

    #-----------------------------------------------------------------------
    def _update(self):
        # TODO: send status command, update internal state
        pass

    #-----------------------------------------------------------------------
