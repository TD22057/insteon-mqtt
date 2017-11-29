#===========================================================================
#
# Message handler API definition
#
#===========================================================================
import time


class Base:
    """Protocol message handler API.

    TODO: doc
    """
    #-----------------------------------------------------------------------
    def __init__(self, time_out=5):
        """Constructor

        Args:
          time_out:  (int) time out in seconds.
        """
        self.time_out = time_out
        self.expire_time = None

    #-----------------------------------------------------------------------
    def update_expire_time(self):
        """Record that valid messages were seen.

        This resets the time out time to record that we saw a valid
        message.
        """
        self.expire_time = time.time() + self.time_out

    #-----------------------------------------------------------------------
    def is_expired(self, protocol, t):
        """See if the time out time has been exceeded.

        This is called periodically to see if the message has expired
        (and can also be used for any polling type behavior.

        Args:
          protocol:  (Protocol) The Insteon Protocol object.
          t:         (float) Current time tag as a Unix clock time.

        Returns:
          Returns True if the message has timed out or False otherwise.
        """
        # Otherwise, result is Msg.UNKNOWN and we should use the time
        # out time to see if the handler has expired.
        return t >= self.expire_time

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
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        raise NotImplementedError("%s.msg_received not implemented" %
                                  self.__class__)

    #-----------------------------------------------------------------------
