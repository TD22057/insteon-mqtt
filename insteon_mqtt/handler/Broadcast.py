#===========================================================================
#
# Insteon broadcast message handler
#
#===========================================================================
import logging
from .. import message as Msg

LOG = logging.getLogger(__name__)


class Broadcast:
    def __init__(self, modem):
        self.modem = modem

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        if not isinstance(msg, Msg.InpStandard):
            return Msg.UNKNOWN

        if msg.flags.type == Msg.Flags.ALL_LINK_BROADCAST:
            device = self.modem.find(msg.from_addr)
            if not device:
                LOG.error("Unknown broadcast device %s", msg.from_addr)
                return Msg.UNKNOWN

            LOG.info("Handling all link broadcast for %s '%s'", device.addr,
                     device.name)
            
            device.handle_broadcast(msg)
            return Msg.FINISHED
            
        elif msg.flags.type == Msg.Flags.ALL_LINK_CLEANUP:
            LOG.info("Ignoring broadcast clean up")
            return Msg.CONTINUE

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
