#===========================================================================
#
# Modem scene  handler.
#
#===========================================================================
from .. import log
from .. import message as Msg
from .Base import Base
from .Flags import Flags

LOG = log.get_logger()


class ModemScene(Base):
    """Modem scene activation handler.

    This handles the callbacks when simulated modem scene is sent using the
    OutModemScene message.  Calls modem.handle_scene when complete.
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
              msg.flags.type == Flags.Type.CLEANUP_ACK and
              msg.group == self.msg.group):
            device = self.modem.find(msg.from_addr)
            if device:
                LOG.debug("%s broadcast to %s for group %s was ack'd",
                          self.modem.label, device.addr, msg.group)
                device.handle_group_cmd(msg.from_addr, msg)
            else:
                LOG.warning("%s broadcast - ack for device %s not found",
                            self.modem.label, msg.from_addr)
            return Msg.CONTINUE

        # Finally there should be an InpAllLinkStatus which tells us the
        # scene command is complete.
        elif isinstance(msg, Msg.InpAllLinkStatus):
            if msg.is_ack:
                LOG.debug("Modem scene %s command ACK", self.msg.group)
                self.modem.handle_scene(self.msg)
                self.on_done(True, "Scene command complete", None)
            else:
                self.on_done(False, "Scene command failed", None)

            return Msg.FINISHED

        # NOTE: The devices in the scene will also send an all link clean up
        # report when they respond.  But we don't need to handle those. The
        # regular device scene broadcast will take care of that.
        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
