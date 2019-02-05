#===========================================================================
#
# Insteon broadcast command response handerl
#
#===========================================================================
from .. import log
from .. import message as Msg
from .Base import Base

LOG = log.get_logger()


class BroadcastCmdResponse(Base):
    """Handles Broadcast Messages Received in Response to a Direct Request`.

    This class handles responses from the device where the device sends an
    ACK but a subsequent broadcast message is sent with the requested payload.

    The handler watches for the proper standard length ACK, returns
    a continue and then waits for the broadcast payload.
    """
    def __init__(self, msg, callback, on_done=None, num_retry=3):
        """Constructor

        Args
          msg (OutStandard):  The output message that was sent.
          callback: Callback function to pass the broadcast messages with
                    that match the desired parameters to.  Signature:
                    callback(message, on_done).
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

        See if the message is the expected ACK of our output or the broadcast
        reply message.  If we get a reply, pass it to the callback.

        Args:
          protocol (Protocol):  The Insteon Protocol object
          msg:  Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        # Probably an echo back of our sent message.
        if isinstance(msg, Msg.OutStandard):
            # If the message is the echo back of our message, then continue
            # waiting for a reply.
            if msg.to_addr == self.addr and msg.cmd1 == self.cmd:
                if not msg.is_ack:
                    LOG.error("%s NAK response", self.addr)

                LOG.debug("%s got msg ACK", self.addr)
                return Msg.CONTINUE

            # Message didn't match the expected addr/cmd.
            LOG.debug("%s handler unknown msg", self.addr)
            return Msg.UNKNOWN

        # Probably an ACK/NAK from the device for our get command.
        elif (isinstance(msg, Msg.InpStandard) and
              msg.flags.type != Msg.Flags.Type.BROADCAST):
            # Filter by address and command.
            if msg.from_addr != self.addr or msg.cmd1 != self.cmd:
                return Msg.UNKNOWN

            if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
                LOG.info("%s device ACK response, waiting for broadcast "
                         "payload", msg.from_addr)
                return Msg.CONTINUE

            elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
                LOG.error("%s device NAK error: %s", msg.from_addr, msg)
                self.on_done(False, "Device command NAK", None)
                return Msg.FINISHED

            else:
                LOG.warning("%s device unexpected msg: %s", msg.from_addr, msg)
                return Msg.UNKNOWN

        # Process the payload reply.
        elif (isinstance(msg, Msg.InpStandard) and
              msg.flags.type == Msg.Flags.Type.BROADCAST):
            # Filter by address and command.
            if msg.from_addr == self.addr:
                # Run the callback - it's up to the callback to check if this
                # is really the ACK or not.
                self.callback(msg, on_done=self.on_done)

                # Indicate no more messages are expected.
                return Msg.FINISHED
            else:
                LOG.info("Possible unexpected broadcast message from %s",
                         msg.from_addr)

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
