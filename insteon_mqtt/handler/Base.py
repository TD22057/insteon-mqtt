#===========================================================================
#
# Message handler API definition
#
#===========================================================================
import time
from .. import log
from .. import message as Msg
from .. import util

LOG = log.get_logger()


class Base:
    """Protocol message handler API.

    This class defines the handler API and implements some basic features
    that all the handlers use like a time out and finished callback.

    Time outs: The Protocol class will call is_expired() at a reasonable
    interval to see if the time out has been reached.  Handlers can use this
    to expire (normal behavior), send addition messages, or whatever custom
    time out behavior they want.  The Protocol will update_expire_time()
    whenever message traffic is received by this handler so that a series of
    messages won't cause the time out to trigger.  If num_retry is set, then
    a message will be retried that many times after a time out.

    Callbacks: most handlers have a "when finished" callback which is run
    when the message sequence is finished.  For convenience, this on_done
    callback is stored in the base class.  The API for the callback is
    always:
       on_done( bool success, str message, data )
    """
    #-----------------------------------------------------------------------
    def __init__(self, on_done=None, num_retry=0, time_out=5):
        """Constructor

        Args:
          on_done:  The finished callback.  Base.on_done will always be
                    callable even if the input is None.
          num_retry (int):  The number of times to retry the message if the
                    handler times out without returning Msg.FINISHED.
                    This count does include the initial sending so a
                    retry of 3 will send once and then retry 2 more times.
          time_out (int):  Time out in seconds.
        """
        self.on_done = util.make_callback(on_done)

        # expire_time is the time after which we should time out.
        self._time_out = time_out
        self._expire_time = None

        # Retry variables.  The message to retry will get set in the
        # sending_message callback.
        self._num_sent = 0
        self._num_retry = num_retry
        self._msg = None

    #-----------------------------------------------------------------------
    def sending_message(self, msg):
        """Messaging being sent callback.

        Protocol calls this to notify us the message is being sent.

        Args:
           msg (message.Base):  The message being sent.
        """
        # Save the message for a later retry if requested.
        self._num_sent += 1
        self._msg = msg

        # Update the expiration time.
        self.update_expire_time()

    #-----------------------------------------------------------------------
    def stop_retry(self):
        """Stop any more retries of sending the message.
        """
        self._msg = None

    #-----------------------------------------------------------------------
    def update_expire_time(self):
        """Record that valid messages were seen.

        This resets the time out time to record that we saw a valid message.
        """
        self._expire_time = time.time() + self._time_out

    #-----------------------------------------------------------------------
    def is_expired(self, protocol, t):
        """See if the time out time has been exceeded.

        This is called periodically to see if the message has expired (and
        can also be used for any polling type behavior.

        Args:
          protocol (Protocol):  The Insteon Protocol object.  Used to allow
                   handler to send more messages if it needs to.
          t (float):  Current time tag as a Unix clock time.

        Returns:
          bool:  Returns True if the message has timed out or False otherwise.
        """
        # Not enough time has elapsed to time out.
        if t < self._expire_time:
            return False

        # If we've exhausted the number of sends, end the handler.
        elif not self._msg or self._num_sent > self._num_retry:
            LOG.warning("Handler timed out - no more retries (%s sent)",
                        self._num_sent - 1)
            self.handle_timeout(protocol)
            return True

        LOG.warning("Handler timed out %s of %s sent: %s",
                    self._num_sent, self._num_retry, self._msg)

        # Increase the hop count if we can.
        if isinstance(self._msg, Msg.OutStandard):  # also handles OutExtended
            num_hops = max(3, self._msg.flags.max_hops)
            LOG.debug("Increasing max_hops to %d", num_hops)
            self._msg.flags.set_hops(num_hops)

        # Otherwise we should try and resend the message with ourselves as
        # the handler again so we don't lose the count.
        protocol.send(self._msg, self)

        # Tell the protocol that we're expired.  This will end this handler
        # and send the next message in the queue.  At some point that will be
        # our retry command with ourselves as the handler again.
        return True

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        This is called by the Protocol when a message is read.  The handler
        can handle the message and continue, handle the message and be
        finished, or pass the message on to other handlers.

        Args:
          protocol (Protocol):  The Insteon Protocol object
          msg:  Insteon message object that was read.

        Returns:
          message.UNKNOWN if we can't handle this message.
          message.CONTINUE if we handled the message and expect more.
          message.FINISHED if we handled the message and are done.
        """
        raise NotImplementedError("%s.msg_received not implemented" %
                                  self.__class__)

    #-----------------------------------------------------------------------
    def handle_timeout(self, protocol):
        """Handle a time out and retry failure occurring.

        This is called when the message sent by the handler has timed out and
        there are no more retries available.

        Args:
          protocol (Protocol):  The Insteon Protocol object.
        """
        self.on_done(False, "Command timed out", None)

    #-----------------------------------------------------------------------
    def __str__(self):
        return "%s handler" % type(self).__name__

    #-----------------------------------------------------------------------
