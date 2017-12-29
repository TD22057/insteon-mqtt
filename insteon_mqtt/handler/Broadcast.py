#===========================================================================
#
# Broadcast message handler.
#
#===========================================================================
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

    This handler will call device.handle_broadcast(msg) for the device that
    sends the message.
    """
    def __init__(self, modem):
        """Constructor

        Args
          modem:   (Modem) The Insteon modem object.
                   Modem.handle_broadcast() is called with the messages
                   that arrive.
        """
        super().__init__()
        self.modem = modem
        self._handled = False

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        Try and process the message. If it's an all link broadcast, find the
        device ID that sent the message from the modem and pass it the
        message so it can send that information to all the devices it's
        connected to for that group.

        Args:
          protocol:  (Protocol) The Insteon Protocol object
          msg:       Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        if not isinstance(msg, Msg.InpStandard):
            return Msg.UNKNOWN

        # Process the all link broadcast.
        if msg.flags.type == Msg.Flags.Type.ALL_LINK_BROADCAST:
            return self._process(msg)

        # Clean up message is basically the same data but addressed to the
        # modem.  If we saw the broadcast, we don't need to handle this.  But
        # if we missed the broadcast, this gives us a second chance to
        # trigger the scene.
        elif msg.flags.type == Msg.Flags.Type.ALL_LINK_CLEANUP:
            if not self._handled:
                return self._process(msg)
            return Msg.FINISHED

        # Different message flags than we exepcted.
        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
    def _process(self, msg):
        """Process the all link broadcast message.

        Args:
          msg:   (Msg.InpStandard) Message to handle.

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

        # Tell the device about it.  This will look up all the responders for
        # this group and tell them that the scene has been activated.
        device.handle_broadcast(msg)
        self._handled = True
        return Msg.FINISHED
