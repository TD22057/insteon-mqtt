#===========================================================================
#
# Message handler API definition
#
#===========================================================================
from .. import message as Msg


class Base:
    """Protocol message handler API.

    TODO: doc
    """
    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        This is called by the Protocol when a message is read.  The
        handler can handle the message and continue, handle the
        message and be finished, or pass the message on to other
        handlers.

        Args:
          protocol:  (Protocol) The Insteon Protocol object
          msg:       Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        raise NotImplementedError("%s.msg_received not implemented" %
                                  self.__class__)

    #-----------------------------------------------------------------------
    def poll(self, t):
        """Periodic polling function.

        The network stack calls this periodically.  This can be used
        to time out message handlers or send new messages (retries,
        cancels, etc).

        Args:
           t:   (float) Current Unix clock time tag.

        Returns:
          Msg.CONTINUE if the handler should still be active.
          Msg.FINISHED if we handler should be removed.
        """
        return Msg.CONTINUE

    #-----------------------------------------------------------------------
