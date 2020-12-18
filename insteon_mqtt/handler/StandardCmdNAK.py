#===========================================================================
#
# Insteon broadcast message handler
#
#===========================================================================
from .. import log
from .. import message as Msg
from .StandardCmd import StandardCmd

LOG = log.get_logger()


class StandardCmdNAK(StandardCmd):
    """Insteon standard input mesage handler that passes on NAKs

    The Standard command handler will process and not pass on Naks to the
    callback function.

    This is handler is identical in everyway, but will pass on a NAK so that
    the callback can process it.  This is rarely needed
    """

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        See if the message is the expected ACK of our output or the expected
        InpStandard reply message.  If we get a reply, pass it to the
        callback.

        Args:
          protocol (Protocol):  The Insteon Protocol object
          msg: Insteon message object that was read.

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
                    LOG.warning("%s PLM NAK response", self.addr)
                else:
                    LOG.debug("%s got PLM ACK", self.addr)
                return Msg.CONTINUE

            # Message didn't match the expected addr/cmd.
            LOG.debug("%s handler unknown msg", self.addr)
            return Msg.UNKNOWN

        # See if this is the standard message ack/nak we're expecting.
        elif isinstance(msg, Msg.InpStandard):
            # If this message matches our address and command, it's probably
            # the ACK we're expecting.
            if msg.from_addr == self.addr and msg.cmd1 == self.cmd:
                # Run the callback it decides what to do with an ACK or NAK
                self.callback(msg, on_done=self.on_done)

                # Indicate no more messages are expected.
                return Msg.FINISHED
            else:
                LOG.info("Possible unexpected message from %s cmd %#04x but "
                         "expected %s cmd %#04x", msg.from_addr, msg.cmd1,
                         self.addr, self.cmd)

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
