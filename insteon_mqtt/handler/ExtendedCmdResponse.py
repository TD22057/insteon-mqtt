#===========================================================================
#
# Device extended response message handler.
#
#===========================================================================
# pylint: disable=too-many-return-statements
from .. import log
from .. import message as Msg
from .Base import Base

LOG = log.get_logger()


class ExtendedCmdResponse(Base):
    """Device extended response message handler.

    This class handles responses from the device where an ACK is made in the
    form of a standard length message and a subsequent extended length
    message is sent with the requested payload.

    The handler watches for the proper standard length ACK, returns a
    continue and then waits for the extended length payload.
    """
    def __init__(self, msg, callback, on_done=None, num_retry=3):
        """Constructor

        The on_done callback has the signature on_done(success, msg, entry)
        and will be called with success=True if the handler finishes
        successfully or False if an error occurs or the handler times out.
        The message input is a string to help with logging the result.

        Args:
          msg (OutStandard):  The output message that was sent.  The reply
              must match the address and msg.cmd1 field to be processed by
              this handler.
          callback:  Callback function to pass InpStandard messages that match
                     the output to.  Signature: callback(message, on_done).
          on_done:  Option finished callback.  This is called when the
                    handler is finished for any reason.
          num_retry (int):  The number of times to retry the message if the
                    handler times out without returning Msg.FINISHED.
                    This count does include the initial sending so a
                    retry of 3 will send once and then retry 2 more times.
        """
        super().__init__(on_done, num_retry)
        self.addr = msg.to_addr
        self.cmd = msg.cmd1
        self.callback = callback

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        See if the message is the expected ACK of our output or the expected
        extended payload message.  If we get the payload, pass it to the
        callback to handle.

        Args:
          protocol (Protocol):  The Insteon Protocol object
          msg:  Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        # Probably an echo back of our sent message.  See if the message
        # matches the address we sent to and assume it's the ACK/NAK message.
        # These seem to be either extended or standard message so allow for
        # both.
        if isinstance(msg, (Msg.OutExtended, Msg.OutStandard)):
            if msg.to_addr == self.addr and msg.cmd1 == self.cmd:
                if not msg.is_ack:
                    LOG.error("%s NAK response", self.addr)
                return Msg.CONTINUE

            return Msg.UNKNOWN

        # Probably an ACK/NAK from the device for our get command.
        elif isinstance(msg, Msg.InpStandard):
            # Filter by address and command.
            if msg.from_addr != self.addr or msg.cmd1 != self.cmd:
                return Msg.UNKNOWN

            if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
                LOG.info("%s device ACK response, waiting for ext payload",
                         msg.from_addr)
                return Msg.CONTINUE

            elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
                LOG.error("%s device NAK error: %s, Message: %s",
                          msg.from_addr, msg.nak_str(), msg)
                self.on_done(False, "Device command NAK. " + msg.nak_str(),
                             None)
                return Msg.FINISHED

            else:
                LOG.warning("%s device unexpected msg: %s", msg.from_addr, msg)
                return Msg.UNKNOWN

        # Process the payload reply.
        elif isinstance(msg, Msg.InpExtended):
            # Filter by address and command.
            if msg.from_addr == self.addr and msg.cmd1 == self.cmd:
                # Run the callback - it's up to the callback to check if this
                # is really the ACK or not.
                self.callback(msg, on_done=self.on_done)

                # Indicate no more messages are expected.
                return Msg.FINISHED
            else:
                LOG.info("Possible unexpected message from %s cmd %#04x but "
                         "expected %s cmd %#04x", msg.from_addr, msg.cmd1,
                         self.addr, self.cmd)

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
