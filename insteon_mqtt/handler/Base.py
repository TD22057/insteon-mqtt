#===========================================================================
#
# Message handler API definition
#
#===========================================================================
import time


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
    def __init__(self, time_out=5, on_done=None):
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
        """
        self._time_out = time_out
        self._expire_time = None
        self.on_done = on_done

        # Use a dummy callback if none was input.  This way we don't
        # have to check if on_done is defined.
        if not on_done:
            self.on_done = lambda *x: x

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
        if t >= self._expire_time:
            self.on_done(False, "Message handler timed out")
            return True

        return False

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
