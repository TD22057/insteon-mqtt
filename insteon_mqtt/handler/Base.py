#===========================================================================
#
# Message handler API definition
#
#===========================================================================
import time
from .. import log

LOG = log.get_logger()


class Base:
    """Protocol message handler API.

    This class defines the handler API and implements some basic
    features that all the handlers use like a time out and finished
    callback.

    Time Outs: The Protocol class will call is_expired() at a
    reasonable interval to see if the time out has been reached.
    Handlers can use this to expire (normal behavior), send addition
    messages, or whatever custom time out behavior they want.  The
    Protocol will update_expire_time() whenever message traffic is
    received by this handler so that a series of messages won't cause
    the time out to trigger.

    Callbac: The on_done
    """
    #-----------------------------------------------------------------------
    def __init__(self, time_out=5, on_done=None, num_retry=0):
        """Constructor

        The on_done callback has the signature on_done(success, msg)
        and will be called with success=True if the handler finishes
        successfully or False if an error occurs or the handler times
        out.  The message input is a string to help with logging the
        result.

        Args:
          time_out:  (int) Time out in seconds.
          on_done:   Option finished callback.  This is called when the
                     handler is finished for any reason.
          num_retry: (int) The number of times to retry the message if the
                     handler times out without returning Msg.FINISHED.
                     This count does include the initial sending so a
                     retry of 3 will send once and then retry 2 more times.
        """
        # expire_time is the time after which we should time out.
        self._time_out = time_out
        self._expire_time = None

        # Retry variables.  The message to retry will get set in the
        # sending_message callback.
        self._num_sent = 0
        self._num_retry = num_retry
        self._msg = None

        # Callback when finished.  Use a dummy callback if none was
        # input.  This way we don't have to check if on_done is defined.
        if on_done:
            self.on_done = on_done
        else:
            self.on_done = lambda *x: x

    #-----------------------------------------------------------------------
    def sending_message(self, msg):
        """Messaging being sent callback.

        The Protocol class calls this to notify that the message is
        being sent.

        Args:
           msg:   (message.Base) The message being sent.
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
        self._num_sent = self._num_retry + 1

    #-----------------------------------------------------------------------
    def update_expire_time(self):
        """Record that valid messages were seen.

        This resets the time out time to record that we saw a valid
        message.
        """
        self._expire_time = time.time() + self._time_out

    #-----------------------------------------------------------------------
    def is_expired(self, protocol, t):
        """See if the time out time has been exceeded.

        This is called periodically to see if the message has expired
        (and can also be used for any polling type behavior.

        Args:
          protocol:  (Protocol) The Insteon Protocol object.  Used to allow
                     handler to send more messages if it needs to.
          t:         (float) Current time tag as a Unix clock time.

        Returns:
          Returns True if the message has timed out or False otherwise.
        """
        # Not enough time has elapsed to time out.
        if t < self._expire_time:
            return False

        # If we've exhausted the number of sends, end the handler.
        elif self._num_sent > self._num_retry or not self._msg:
            LOG.warning("Handler timed out - no more retries (%s sent)",
                        self._num_sent)
            self.on_done(False, "Message handler timed out")
            return True

        LOG.warning("Handler timed out %s of %s sent: %s",
                    self._num_sent, self._num_retry, self._msg)

        # Otherwise we should try and resend the message with
        # ourselves as the handler again so we don't lose the count.
        self._num_sent += 1
        protocol.send(self._msg, self)

        # Tell the protocol that we're expired.  This will end this
        # handler and send the next message in the queue.  At some
        # point that will be our retry command with ourselves as the
        # handler again.
        return True

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        This is called by the Protocol when a message is read.  The
        handler can handle the message and continue, handle the
        message and be finished, or pass the message on to other
        handlers.

        Args:
          protocol:  (Protocol) The Insteon Protocol object.
          msg:       Insteon message object that was read.

        Returns:
          message.UNKNOWN if we can't handle this message.
          message.CONTINUE if we handled the message and expect more.
          message.FINISHED if we handled the message and are done.
        """
        raise NotImplementedError("%s.msg_received not implemented" %
                                  self.__class__)

    #-----------------------------------------------------------------------
