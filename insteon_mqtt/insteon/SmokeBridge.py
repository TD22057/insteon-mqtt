#===========================================================================
#
# SmokeBridge module
#
#===========================================================================
from .Device import Device
from .. import Signal
import logging

s_log = logging.getLogger(__name__)

class SmokeBridge (Device):
    def __init__(self, handler, address, name=None):
        super().__init__(handler, address, name)

        self.signal_smoke = Signal.Signal()
        self.signal_co = Signal.Signal()
        self.signal_test = Signal.Signal()
        self.signal_battery = Signal.Signal()
        self.signal_error = Signal.Signal()
        self.signal_heartbeat = Signal.Signal()

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
