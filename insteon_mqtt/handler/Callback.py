#===========================================================================
#
# Simple command ACK/NAK handler.
#
#===========================================================================
import inspect
import logging
from .. import message as Msg
from .Base import Base

LOG = logging.getLogger(__name__)


class Callback(Base):
    """Basic callback handler.

    This handler will call the input callback when the input message
    type matches the message class or message instance passed to the
    constructor.
    """
    def __init__(self, msg, callback=None):
        """Constructor

        Args
          msg:       The message being to match or the message class to match.
          callback:  Optional callback to call when the message is matched.
                     Signature is callback(msg) where msg is the message
                     passed to msg_received.
        """
        super().__init__()

        if inspect.isclass(msg):
            self.msg_type = msg
        else:
            self.msg_type = type(msg)

        self.callback = callback

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        Try and process the message. If it matches the outbound
        message, pass it to the callback.

        Args:
          protocol:  (Protocol) The Insteon Protocol object
          msg:       Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.FINISHED if we handled the message and are done.
        """
        if not isinstance(msg, self.msg_type):
            return Msg.UNKNOWN

        # Pass the message to the callback.
        if self.callback:
            self.callback(msg)

        return Msg.FINISHED

    #-----------------------------------------------------------------------
