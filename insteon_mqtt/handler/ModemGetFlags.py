#===========================================================================
#
# Modem get_flags handler.
#
#===========================================================================
from .. import log
from .. import message as Msg
from .Base import Base

LOG = log.get_logger()


class ModemGetFlags(Base):
    """Modem get_flags handler.

    This handles a `get flags` command being sent to the modem. The response
    to this command is a single message containing the flags and 2 spare
    bytes.
    """
    def __init__(self, modem, on_done=None):
        """Constructor

        Args
          modem (Modem):  The Insteon modem object.
          on_done: The finished callback.  Calling signature:
                   on_done( bool success, str message, data )
        """
        super().__init__(on_done)

        self.modem = modem

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        If we get an ACK of the user reset, we'll clear the modem database.

        Args:
          protocol  (Protocol):  The Insteon Protocol object
          msg:  Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        if not self._PLM_sent:
            # If PLM hasn't sent our message yet, this can't be for us
            return Msg.UNKNOWN
        if isinstance(msg, Msg.OutGetModemFlags):
            if msg.is_ack:
                LOG.ui("Modem flag byte is: %s, spare bytes are: %s, %s",
                       msg.modem_flags, msg.spare1, msg.spare2)
                self.on_done(True, "Modem get_flags complete", None)
            else:
                LOG.error("Modem get_flags failed")
                self.on_done(False, "Modem get_flags failed", None)

            return Msg.FINISHED

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
