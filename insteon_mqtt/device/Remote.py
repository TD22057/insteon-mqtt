#===========================================================================
#
# Dimmer module
#
#===========================================================================
import logging
from .Base import Base

LOG = logging.getLogger(__name__)


class Remote(Base):
    def __init__(self, protocol, modem, address, num, name=None):
        super().__init__(protocol, modem, address, name)
        self.num = num
        self._is_on = [None]*num

    #-----------------------------------------------------------------------
    def pair(self):
        LOG.info("Remote %s pairing with modem", self.addr)
        # TODO: pair with modem

    #-----------------------------------------------------------------------
    def is_on(self, button):
        return not self._is_on[button]

    #-----------------------------------------------------------------------
    def on(self, button, instant=False):
        LOG.info("Remote %s btn: %s cmd: on", self.addr, button)

        # We can't inject a broadcast message from the device into the
        # network.  So to simulate a button on press on the remote,
        # look up each device in the link database and simulate the
        # message being sent to them so they'll update to the correct
        # levels.
        # TODO: simulate on command

    #-----------------------------------------------------------------------
    def off(self, button, instant=False):
        LOG.info("Remote %s btn: %s cmd: off", self.addr, button)
        # TODO: simulate on command

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
