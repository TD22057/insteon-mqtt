#===========================================================================
#
# Device get all link database handler.
#
#===========================================================================
import logging
from .. import message as Msg
from .Base import Base

LOG = logging.getLogger(__name__)


class DeviceGetDb(Base):
    """Device database request message handler.

    To download the all link database from a device, we send a
    request.  The output message gets ACK'ed back to us.  Then the
    device sends us a series of messages with the database entries.
    The last message will be all zeros to indicate no more records.

    Each reply is passed to the callback function set in the
    constructor which is usually a method on the device to update it's
    database.
    """
    def __init__(self, addr, callback):
        """Constructor

        Args
          addr:    (Address) The address of the device we're expecting
          callback: Callback function to pass database messages to or None
                    to indicate the end of the entries.
        """
        super().__init__()

        self.addr = addr
        self.callback = callback
        self._have_ack = False

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        See if the message is the expected ACK of our output or the
        expected database reply message.  If we get a reply, pass it
        to the device to update it's database with the info.

        Args:
          protocol:  (Protocol) The Insteon Protocol object
          msg:       Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        # Probably an echo back of our sent message.  See if the
        # message matches the address we sent to and assume it's the
        # ACK/NAK message.  These seem to be either extended or
        # standard message so allow for both.
        if isinstance(msg, (Msg.OutExtended, Msg.OutStandard)):
            if msg.to_addr == self.addr and msg.cmd1 == 0x2f:
                if not msg.is_ack:
                    LOG.error("%s NAK response", self.addr)
                return Msg.CONTINUE

            return Msg.UNKNOWN

        # Process the real reply.  Database reply is an extended messages.
        elif isinstance(msg, Msg.InpExtended):
            # Filter by address and command.
            if msg.from_addr != self.addr or msg.cmd1 != 0x2f:
                return Msg.UNKNOWN

            # If all the data elements are zero, this is the last
            # device database record and we can return FINISHED.
            sum = 0
            for i in msg.data[4:13]:
                sum += i
            if sum == 0x00:
                self.callback(None)
                return Msg.FINISHED

            # Pass the record to the callback and wait for more messages.
            self.callback(msg)
            return Msg.CONTINUE

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
