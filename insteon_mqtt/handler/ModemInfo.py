#===========================================================================
#
# Modem get_info handler.
#
#===========================================================================
from .. import log
from .. import message as Msg
from .Base import Base

LOG = log.get_logger()


class ModemInfo(Base):
    """Modem get_info handler.

    This is primarily used to get the modem address on startup.
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
        if isinstance(msg, (Msg.OutModemInfo)):
            if msg.is_ack:
                self.on_done(True, "Modem get info success", msg)
            else:
                LOG.error("Modem get_info failed.")
                self.on_done(False, "Modem get_info failed", msg)

            return Msg.FINISHED

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
