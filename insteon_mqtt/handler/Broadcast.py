#===========================================================================
#
# Broadcast message handler.
#
#===========================================================================
import time
from .. import log
from .. import message as Msg
from .Base import Base

LOG = log.get_logger()


class Broadcast(Base):
    """Broadcast message handler.

    Broadcast messages are sent when a device is triggered manually like
    pushing a light switch or a motion sensor.  The message is an all link
    broadcast which says 'address AA.BB.CC activate group DD' and any device
    in that is a responder to that group will activate.

    The message sequence is an ALL_LINK_BROADCAST which we can get the device
    address and group from.  Then an ALL_LINK_CLEANUP is sent.  Both messages
    can be used to trigger the scene but we'll only do that once (so the 2nd
    message gets ignored).  So if we get the broadcast, the cleanup is
    ignored.

    Finally a broadcast LINK_CLEANUP_REPORT is sent.  This message indicates
    if the device received ACKs from all linked devices or not.  This message
    indicates that the device is finished sending messages.  However, as
    broadcast message, it is not guaranteed to be received.

    This handler will call device.handle_broadcast(msg) for the device that
    sends the message.

    NOTE: This handler is designed to always be active - it never returns
    FINISHED.
    """
    def __init__(self, modem):
        """Constructor

        Args
          modem (Modem):  The Insteon modem object. Modem.handle_broadcast()
                is called with the messages that arrive.
        """
        super().__init__()
        self.modem = modem

        # We get a broadcast, then a cleanup.  So when we receive the
        # broadcast, store it here.  That way when we see the cleanup, we
        # don't call the device again.  But if we miss the broadcast, the
        # cleanup will trigger the device call.
        self._last_broadcast = None

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        Try and process the message. If it's an all link broadcast, find the
        device ID that sent the message from the modem and pass it the
        message so it can send that information to all the devices it's
        connected to for that group.

        Args:
          protocol (Protocol):  The Insteon Protocol object
          msg:  Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        if not isinstance(msg, Msg.InpStandard):
            return Msg.UNKNOWN

        # Calculate the total time this process could take
        # A device broadcast will be followed up a series of cleanup messages
        # between the devices and sent to the modem.  Don't send anything
        # during this time to avoid causing a collision.  Time is equal to .5
        # second of overhead, plus .522 seconds per responer device.  This is
        # based off the same 87 msec empircal testing performed when designing
        # misterhouse.  Each device causes a cleanup and an ack.  Assuminng
        # a max of three hops in each direction that is 6 * .087 or .522 per
        # device.
        device = self.modem.find(msg.from_addr)
        wait_time = 0
        if device:
            responders = device.db.find_group(msg.group)
            wait_time = .5 + (len(responders) * .522)

        # Process the all link broadcast.
        if msg.flags.type == Msg.Flags.Type.ALL_LINK_BROADCAST:
            if msg.cmd1 == Msg.CmdType.LINK_CLEANUP_REPORT:
                # This is the final broadcast signalling completion.
                # All of these messages will be forwarded to the device
                # potentially even duplicates
                # Re-enable sending
                # First clear wait time
                protocol.set_wait_time(0)
                # Then set as expire time of this message
                protocol.set_wait_time(msg.expire_time)
                # cmd2 identifies the number of failed devices
                if msg.cmd2 == 0x00:
                    LOG.debug("Cleanup report for %s, grp %s success.",
                              msg.from_addr, msg.group)
                else:
                    text = "Cleanup report for %s, grp %s had %d fails."
                    LOG.warning(text, msg.from_addr, msg.group, msg.cmd2)
                return self._process(msg, protocol, wait_time)
            else:
                # This is the initial broadcast or an echo of it.
                if self._should_process(msg, wait_time):
                    return self._process(msg, protocol, wait_time)
                else:
                    return Msg.CONTINUE

        # Clean up message is basically the same data but addressed to the
        # modem.  If we saw the broadcast, we don't need to handle this.  But
        # if we missed the broadcast, this gives us a second chance to
        # trigger the scene.
        elif msg.flags.type == Msg.Flags.Type.ALL_LINK_CLEANUP:
            if self._should_process(msg, wait_time):
                return self._process(msg, protocol, wait_time)
            else:
                return Msg.CONTINUE

        # Different message flags than we expected.
        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
    def _process(self, msg, protocol, wait_time):
        """Process the all link broadcast message.

        Args:
          msg (Msg.InpStandard):  Message to handle.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        # Find the device that sent the message.
        device = self.modem.find(msg.from_addr)
        if not device:
            LOG.error("Unknown broadcast device %s", msg.from_addr)
            return Msg.UNKNOWN

        LOG.info("Handling all link broadcast for %s '%s'", device.addr,
                 device.name)

        # Save for deduplication detection
        self._last_broadcast = msg

        # Delay sending, see above
        protocol.set_wait_time(time.time() + wait_time)

        # Tell the device about it.  This will look up all the responders for
        # this group and tell them that the scene has been activated.
        device.handle_broadcast(msg)
        return Msg.CONTINUE

    #-----------------------------------------------------------------------
    def _should_process(self, msg, wait_time):
        """Should we process a cleanup message?

        Checks if this is a duplicate of a message we have already seen.

        Args:
          msg (Msg.InpStandard):  Cleanup message to handle.
          wait_time (float):      The number of seconds this process could
                                  take to complate.  Used to find duplicates

        Returns:
          bool:  True if the message should be procssed, False otherwise.
        """
        if not self._last_broadcast:
            return True

        # Don't process the message if we just got a corresponding broadcast
        # message from the same device.  Wait time plus expire time is used
        # to ignore old messages.  Expire_time adds more time then we need
        # but the timings don't have to be perfect
        if (self._last_broadcast.from_addr == msg.from_addr and
                self._last_broadcast.group == msg.group and
                self._last_broadcast.cmd1 == msg.cmd1 and
                self._last_broadcast.expire_time + wait_time > time.time()):
            return False

        return True
