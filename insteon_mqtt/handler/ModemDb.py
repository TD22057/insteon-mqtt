#===========================================================================
#
# Insteon broadcast message handler
#
#===========================================================================
import logging
from .. import message as Msg

LOG = logging.getLogger(__name__)


class ModemDb:
    """PLM Modem database request message handler.

    To download the all link database from the PLM modem, we send a
    request.  The output message gets ACK'ed back to us.  Then the
    modem sends us a single record.  After we receive the record, we
    send another message out requesting the next record, etc, etc
    until we get a NAK to indicate there are no more records.

    Each reply is passed to the modem.handle_db_rec to update it's
    database.
    """
    def __init__(self, modem):
        """Constructor

        Args
          modem:   (Modem) The Insteon modem.
        """
        self.modem = modem

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        See if the message is the expected ACK of our output or the
        expected database reply message.  If we get a reply, pass it
        to the modem to update it's database with the info.

        Args:
          protocol:  (Protocol) The Insteon Protocol object
          msg:       Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        # Message is an ACK/NAK of the record request.
        if isinstance(msg, (Msg.OutAllLinkGetFirst, Msg.OutAllLinkGetNext)):
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
