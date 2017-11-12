#===========================================================================
#
# Insteon broadcast message handler
#
#===========================================================================
import logging
from .. import message as Msg

LOG = logging.getLogger(__name__)


class StandardCmd:
    def __init__(self, msg, callback, cmd=None):
        self.addr = msg.to_addr
        self.cmd = msg.cmd1 if cmd is None else cmd
        self.callback = callback

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        # Probably an echo back of our sent message.
        if isinstance(msg, Msg.OutStandard):
            # If the message is the echo back of our message, then
            # continue waiting for a reply.
            if self._match(msg.to_addr, msg.cmd1):
                if not msg.is_ack:
                    LOG.error("%s NAK response", self.addr)

                LOG.debug("%s got msg ACK", self.addr)
                return Msg.CONTINUE

            LOG.debug("%s handler unknown msg", self.addr, msg)
            return Msg.UNKNOWN

        # See if this is the standard message ack/nak we're expecting.
        if isinstance(msg, Msg.InpStandard):
            # If this message matches our address and command, it's
            # probably the ACK we're expecting.
            if self._match(msg.from_addr, msg.cmd1):
                # Run the callback - it's up to the callback to check
                # if this is an ACK or not.
                self.callback(msg)

                # Indicate no more messages are expected.
                return Msg.FINISHED
            else:
                LOG.info("Possible unexpected message from %s cmd %#04x but "
                         "expected %s cmd %#04x", msg.from_addr, msg.cmd1,
                         self.addr, self.cmd)

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
    def _match(self, addr, cmd):
        if addr != self.addr:
            return False

        if self.cmd != -1 and cmd != self.cmd:
            return False

        return True
        
            
    #-----------------------------------------------------------------------
