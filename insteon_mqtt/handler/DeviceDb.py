#===========================================================================
#
# Insteon broadcast message handler
#
#===========================================================================
import logging
from .. import message as Msg

LOG = logging.getLogger(__name__)


class DeviceDb:
    def __init__(self, addr, callback):
        self.addr = addr
        self.callback = callback
        self.have_ack = False

    #-----------------------------------------------------------------------
    def msg_received(self, transport, msg):
        # Probably an echo back of our sent message.
        if isinstance(msg, Msg.OutExtended):
            if msg.to_addr == self.addr and msg.cmd1 == 0x2f:
                if not msg.is_ack:
                    LOG.error("%s NAK response", self.addr)
                    
                return Msg.CONTINUE

            return Msg.UNKNOWN

        # Probably an ACK of our command.
        elif isinstance(msg, Msg.OutStandard):
            if msg.to_addr != self.addr or msg.cmd1 != 0x2f:
                return Msg.UNKNOWN

            self.have_ack = True
            LOG.info("received direct ack %s", self.addr)
            return Msg.CONTINUE

        # Extended messages are probably the database records we
        # requested.
        elif isinstance(msg, Msg.InpExtended):
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

            # Pass the record to the callback and wait for more
            # messages.
            self.callback(msg)
            return Msg.CONTINUE

        return Msg.UNKNOWN
    
    #-----------------------------------------------------------------------
