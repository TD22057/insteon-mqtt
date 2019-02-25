#===========================================================================
#
# Timed message class
#
#===========================================================================


class Timed:
    """Timed message container

    This stores a message and time at which the message should be sent and is
    used by the Protocol class for storing a message that should be sent at
    some later time.
    """

    #-----------------------------------------------------------------------
    def __init__(self, msg, msg_handler, high_priority, after):
        """Constructor

        Args:
          msg:  Output message to write.  This should be an instance of a
                message in the message directory that that starts with 'Out'.
          msg_handler:  Message handler instance to use when replies to the
                        message are received.  Any message received after we
                        write out the msg are passed to this handler until
                        the handler returns the message.FINISHED flags.
          high_priority (bool):  False to add the message at the end of the
                        queue.  True to insert this message at the start of
                        the queue.  This is ignored in timed messages.
          after (float):  Unix clock time tag to send the message after. If
                None, the message is sent as soon as possible.  Exact time is
                not guaranteed - the message will be send no earlier than this.
        """
        self.msg = msg
        self.msg_handler = msg_handler
        self.high_priority = high_priority
        self.time = after

    #-----------------------------------------------------------------------
    def is_active(self, t):
        """Return True if the message should be sent.

        Args:
          t (float):  Current Unix clock time.
        """
        return t >= self.time

    #-----------------------------------------------------------------------
    def send(self, protocol):
        """Send the message.

        Args:
          protocol (Protocol):  The Protocol class to use.
        """
        protocol.send(self.msg, self.msg_handler, self.high_priority)

#===========================================================================
