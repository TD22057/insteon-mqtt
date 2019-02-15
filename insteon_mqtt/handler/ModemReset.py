#===========================================================================
#
# Modem factory reset handler.
#
#===========================================================================
from .. import log
from .. import message as Msg
from .Base import Base

LOG = log.get_logger()


class ModemReset(Base):
    """Modem being factory reset handler.

    This handles a factory reset command being sent to the modem and the
    physically triggering a factory reset on the modem with the set button.

    When this happens, we'll clear the modem all link database.
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
        # InpUserReset is sent when the user triggers a factory reset
        #     on the physical modem.
        # OutResetModem is sent when we send that command to the modem
        #     to reset it and we'll get an ack/nak back.
        if isinstance(msg, (Msg.OutResetModem, Msg.InpUserReset)):
            if msg.is_ack:
                LOG.warning("Modem has been factory reset")

                # Erase the local modem database.  This also erases the
                # on-disk store of the database.
                self.modem.db.clear()
                self.on_done(True, "Modem has been reset", None)
            else:
                LOG.error("Modem factory reset failed")
                self.on_done(False, "Modem reset failed", None)

            return Msg.FINISHED

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
