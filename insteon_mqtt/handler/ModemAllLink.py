#===========================================================================
#
# Modem all link mode handler.
#
#===========================================================================
import logging
from .. import message as Msg
from .Base import Base

LOG = logging.getLogger(__name__)


class ModemAllLink(Base):
    """Modem all link mode message handler.

    This is used when the modem is placed in all-link mode (like
    pressing the set button).  We expect to get an ACK of the
    OutAllLinkStart message first.  If the all link mode is canceled,
    we'll get an OutAllLinkCancel ACK.  If linking completes (a device
    set button is held down to finish the link), we'll get an
    InpAllLinkComplete message

    If no reply is received in the time out window, we'll send an
    OutAllLinkCancel message.
    """
    def __init__(self, protocol, callback, time_out=60):
        """Constructor

        Args
          protocol: (Protocol) The Insteon protocol object.
          callback: Callback function to pass database messages to or None
                    to indicate the end of the entries.
          time_out: (int) Time out in seconds.  If we don't get an
                    InpAllLinkComplete message in this time, we'll send a
                    cancel message to the modem to cancel the all link mode.
        """
        super().__init__(time_out)

        self.protocol = protocol
        self.callback = callback

    #-----------------------------------------------------------------------
    def is_expired(self, t):
        """See if the time out time has been exceeded.

        Args:
          t:  (float) Current time tag as a Unix clock time.

        Returns:
          Returns True if the message has timed out or False otherwise.
        """
        # If we haven't expired, return.
        if not super().is_expired(t):
            return

        # Linking window has expired.  Set a cancel command at the
        # start of the message queue so it gets sent next.
        msg = Msg.OutAllLinkCancel()
        msg_handler = self
        self.protocol.send(msg, msg_handler, high_priority=True)

        # Tell the protocol that we're expired.  This will end this
        # handler and send the next message which is the cancel
        # message we just added at the start of the queue with
        # ourselves as the handler.
        return Msg.FINISHED

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
        # Message is an ACK of the all link activation.
        if isinstance(msg, Msg.OutAllLinkStart):
            # If we get a NAK, then an error occured.
            if not msg.is_ack:
                LOG.error("Modem did not enter all link mode - NAK received")
                return Msg.FINISHED

            # ACK - wait for more messages.
            return Msg.CONTINUE

        # All linking was successful.
        elif isinstance(msg, Msg.InpAllLinkComplete):
            # Run the callback and tell the protocol we're finished.
            self.callback(msg)
            return Msg.FINISHED

        # All linking was canceled.  It probably doesn't matter if
        # this is an ack or nak - either way we're not going to link.
        elif isinstance(msg, Msg.OutAllLinkCancel):
            LOG.info("Modem all link mode canceled.")
            return Msg.FINISHED

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
