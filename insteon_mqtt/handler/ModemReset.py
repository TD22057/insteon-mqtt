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
    """TODO: handles user reset or reset by command.


    This is used when the modem is placed in all-link mode (like
    pressing the set button).  We expect to get an ACK of the
    OutAllLinkStart message first.  If the all link mode is canceled,
    we'll get an OutAllLinkCancel ACK.  If linking completes (a device
    set button is held down to finish the link), we'll get an
    InpAllLinkComplete message

    If no reply is received in the time out window, we'll send an
    OutAllLinkCancel message.
    """
    def __init__(self, modem):
        """Constructor

        Args
          protocol: (Protocol) The Insteon protocol object.
          callback: Callback function to pass database messages to or None
                    to indicate the end of the entries.
          time_out: (int) Time out in seconds.  If we don't get an
                    InpAllLinkComplete message in this time, we'll send a
                    cancel message to the modem to cancel the all link mode.
        """
        super().__init__()

        self.modem = modem

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        If all linking is finished, pass the message to the callback
        to update the device records (or re-download the database) if
        needed.

        Args:
          protocol:  (Protocol) The Insteon Protocol object
          msg:       Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.

        """
        # InpUserReset is sent when the user triggers a factory reset
        #     on the physical modem.
        # OutResetPlm is sent when we send that command to the modem
        #     to reset it and we'll get an ack/nak back.
        if isinstance(msg, (Msg.OutResetPlm, Msg.InpUserReset)):
            if msg.is_ack:
                LOG.warning("Modem has been factory reset")

                # Erase the local modem database.  This also erases the
                # on-disk store of the database.
                self.modem.db.clear()
            else:
                LOG.error("Modem factory reset failed")

            return Msg.FINISHED

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
