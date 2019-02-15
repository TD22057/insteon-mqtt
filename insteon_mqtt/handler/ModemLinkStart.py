#===========================================================================
#
# Modem all link starting handler.
#
#===========================================================================
from .. import log
from .. import message as Msg
from .Base import Base

LOG = log.get_logger()


class ModemLinkStart(Base):
    """Modem linking starting message handler.

    This is used when the modem is entering linking mode.  It listens for an
    ACK of the message to show that the command worked.  When a pairing is
    created, that message is handled by the ModemLinkComplete handler which
    is always injstalled.
    """
    def __init__(self, on_done=None):
        """Constructor

        Args:
          on_done:  The finished callback.  Calling signature:
                    on_done( bool success, str message, data )
        """
        # pylint: disable=useless-super-delegation
        super().__init__(on_done)

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        Args:
          protocol (Protocol):  The Insteon Protocol object
          msg:  Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        if not isinstance(msg, Msg.OutModemLinking):
            return Msg.UNKNOWN

        # Message is an ACK of the all link activation.
        if msg.is_ack:
            LOG.debug("ModemLinkStart got msg ACK")
            self.on_done(True, "Modem entering linking mode", None)

        # If we get a NAK, then an error occured.
        else:
            LOG.error("Modem did not enter all link mode - NAK received")
            self.on_done(False, "Modem linking mode failed", None)

        return Msg.FINISHED

    #-----------------------------------------------------------------------
