#===========================================================================
#
# Modem get all link database handler.
#
#===========================================================================
import logging
from .. import message as Msg
from .Base import Base

LOG = logging.getLogger(__name__)


class ModemGetDb(Base):
    """PLM Modem database request message handler.

    To download the all link database from the PLM modem, we send a
    request.  The output message gets ACK'ed back to us.  Then the
    modem sends us a single record.  After we receive the record, we
    send another message out requesting the next record, etc, etc
    until we get a NAK to indicate there are no more records.

    Each reply is passed to the callback function set in the
    constructor which is usually a method on the device to update it's
    database.
    """
    def __init__(self, modem, callback):
        """Constructor

        Args
          modem:    (Modem) The Insteon modem.
          callback: Callback function to pass database messages to or None
                    to indicate the end of the entries.
        """
        super().__init__()

        self.modem = modem
        self.callback = callback

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
                self.callback(None)
                return Msg.FINISHED

            # ACK - keep reading until we get the record we requested.
            return Msg.CONTINUE

        # Message is the record we requested.
        if isinstance(msg, Msg.InpAllLinkRec):
            LOG.info("Modem db record received")
            self.callback(msg)

            # Request the next record in the PLM database.
            LOG.info("Modem requesting next db record")
            msg = Msg.OutAllLinkGetNext()
            protocol.send(msg, self)

            # Return finished - this way the getnext message will go
            # out.  We'll be used as the handler for that as well
            # which repeats until we get a nak response (handled
            # above).
            return Msg.FINISHED

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
