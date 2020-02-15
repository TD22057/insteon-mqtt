#===========================================================================
#
# Modem scene  handler.
#
#===========================================================================
from .. import log
from .. import message as Msg
from .Base import Base
from ..message.Flags import Flags

LOG = log.get_logger()


class ModemScene(Base):
    """Modem scene activation handler.

    This handles the callbacks when simulated modem scene is sent using the
    OutModemScene message.  Calls modem.handle_scene when complete.

    Modem scene controls are complicated things.  Their main feature is that
    from an end-user's perspective and if the message is received correctly
    all devices seem to change instananeously and at once.

    However, because of the complexity of the task the modem is asked to
    perform, it seems that if the modem is interrupted by any extraneous
    Insteon message while performing the scene command, it may somewhat lose
    its mind.

    It appears the the Modem still continues to process everything correctly
    but the messages it reports to the host can appear wrong.  Such as wrong
    groups reported, CLEANUP_NAKs that are wrong, wrong InpAllLinkFailure
    reports and even a wrong or premature InpAllLinkStatus NAK.

    We can't do anything with these messages when they arrive, since we don't
    know what they should have meant.  However, if we extend the time_out each
    time we receive one of these garbled messages, we eventually will receive
    a correct InpAllLinkStatus ACK.  To the extent we can identify any of
    these messages as meant for this handler, we report them to the user for
    potential debugging.
    """
    def __init__(self, modem, msg, on_done=None, num_retry=3):
        """Constructor

        Args
          modem (Modem):  The Insteon modem object.
          msg (OutModemScene):  The scene message being sent.
          on_done: The finished callback.  Calling signature:
                   on_done( bool success, str message, data )
          num_retry (int):  The number of times to retry the message if the
                    handler times out without returning Msg.FINISHED.
                    This count does include the initial sending so a
                    retry of 3 will send once and then retry 2 more times.
        """
        super().__init__(on_done, num_retry)

        self.modem = modem
        self.msg = msg

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        Args:
          protocol (Protocol):  The Insteon Protocol object
          msg: Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        # We should get an initial ack of the scene message
        if isinstance(msg, Msg.OutModemScene):
            if msg.is_ack:
                return Msg.CONTINUE

            # NAK - modem not connected?
            self.on_done(False, "Scene command failed", None)
            return Msg.FINISHED

        # Next we should get cleanup_acks from each device
        elif (isinstance(msg, Msg.InpStandard) and
              msg.flags.type == Flags.Type.CLEANUP_ACK):
            if msg.group != self.msg.group:
                # This isn't the right group, but extend the waiting time to
                # see if we get more messages, but report as unknown in case
                # another handler can do something with this.
                self.update_expire_time()
                return Msg.UNKNOWN
            else:
                # Trigger an update of our internal state of this device
                device = self.modem.find(msg.from_addr)
                if device:
                    LOG.debug("%s broadcast to %s for group %s was ack'd",
                              self.modem.label, device.addr, msg.group)
                    device.handle_group_cmd(self.modem.addr, self.msg)
                else:
                    LOG.warning("%s broadcast - ack for device %s not found",
                                self.modem.label, msg.from_addr)

                return Msg.CONTINUE

        # This is an all link failure report.
        elif isinstance(msg, Msg.InpAllLinkFailure):
            if msg.group != self.msg.group:
                # This isn't the right group, but extend the waiting time to
                # see if we get more messages, but report as unknown in case
                # another handler can do something with this.
                self.update_expire_time()
                return Msg.UNKNOWN
            else:
                LOG.error("%s failed to respond to broadcast for group %s",
                          msg.addr, msg.group)
                return Msg.CONTINUE

        # This is a NAK response from a device.
        elif (isinstance(msg, Msg.InpStandard) and
              msg.flags.type == Flags.Type.CLEANUP_NAK):
            # NAK responses have no group details cmd2 in theory contains a
            # reason for the failure, but in practice isn't helpful
            LOG.error("%s responded NAK to broadcast for group %s",
                      msg.from_addr, self.msg.group)
            return Msg.CONTINUE

        # Finally there should be an InpAllLinkStatus which tells us the
        # scene command is complete.
        elif isinstance(msg, Msg.InpAllLinkStatus):
            if msg.is_ack:
                LOG.debug("Modem scene %s command ACK", self.msg.group)
                self.modem.handle_scene(self.msg)
                self.on_done(True, "Scene command complete", None)
            else:
                # The modem seems to automatically retry even after sending a
                # NAK, so just wait.  If the timeout occurs we will resend
                # then
                LOG.warning("Modem scene %s NAK, waiting...", self.msg.group)
                return Msg.CONTINUE

            return Msg.FINISHED

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
