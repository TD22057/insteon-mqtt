#===========================================================================
#
# Insteon broadcast message handler
#
#===========================================================================
import logging
from .. import message as Msg

LOG = logging.getLogger(__name__)


class ModemDb:
    def __init__(self, modem):
        self.modem = modem
        
    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        # Message is an ACK/NAK of the record request.
        if (isinstance(msg, Msg.OutAllLinkGetFirst) or
            isinstance(msg, Msg.OutAllLinkGetNext)):
            # If we get a NAK, then there are no more db records.
            if not msg.is_ack:
                LOG.info("Modem finished - last db record received")
                self.modem.handle_db_rec(None)
                return Msg.FINISHED

            # ACK - keep reading until we get the record we requested.
            return Msg.CONTINUE

        # Message is the record we requested.
        if isinstance(msg, Msg.InpAllLinkRec):
            LOG.info("Modem db record received")
            self.modem.handle_db_rec(msg)

            # Request the next record in the PLM database.
            LOG.info("Modem requesting next db record")
            msg = Msg.OutAllLinkGetNext()
            protocol.send(msg, self)
            return Msg.CONTINUE

        return Msg.UNKNOWN
        
    #-----------------------------------------------------------------------
