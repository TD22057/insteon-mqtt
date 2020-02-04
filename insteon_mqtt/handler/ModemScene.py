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

    However, it seems that because of the complexity of the task the modem is
    asked to perform, it seems that if the modem is interrupted by any
    extraneous Insteon message while performing the scene command, it may
    somewhat lose its mind.  This message can originate from the host side of
    the modem.  We attempt to prevent this by using appropriate delays before
    writing.  But the interruptions can also occur from the Insteon network
    for example if another device is triggered while the scene command is
    processing.  This we can't control.

    The process of a scene command looks like:
    1. Send command to modem from host
    2. Modem ACKs the command back to host
    3. Modem sends a broadcast message on the insteon network.
    4. Modem sends individual cleanup messages to each device in the group on
       the insteon network
    5. Devices ACK the cleanup messages
    6. The modem reports the ACKs to the host
    7. If any failures occur, the modem delivers a cleanup report to the host
    8. The modem delivers a scene ACK or NAK report to the host

    The cleanup process (4-6) can take between 1/3 to 1/2 second per device. So
    for example, on my network a scene command sent to 50 devices can take
    20 seconds to complete.

    During this time, if another device on the insteon network sends a message
    to the modem, things can go sideways.  These are some of the things I have
    seen:
    - Step 6 - The modem ACKs contain the wrong group.  Commonly group 0xFF
    - Step 6 - Shortly after the prior oddity, the modem simply reports all
               CLEANUP_NAK messages, even though the devices themselves
               correctly respond to the command
    - Step 6 - If an ACK is reported with the proper group, it seems to be
               always correct.  I have never seen a false positive of this.
    - Step 7 - The cleanup report identifies 1 or more devices that did not ACK
               the cleanup command, but again frequently gets the group number
               of the command wrong.  And in almost all cases, the devices
               listed in this report are only a subset of the devices with
               reported NAKs.
    - Step 8 - Generally, if any of the above occurs, a NAK is delivered.  I
               have never seen an ACK that was a false positive.

    Taking all of this into account, our method of handling scene commands is
    as follows:
    1. Generate a list of all devices that should respond to the scene command
    2. Send the scene command using the modem
    3. For every device ACK received remove that device from the dev_list
    4. Catch NAK commands and report them if we can (some may have the wrong
       group number, in which case these remain un handled) do nothing
    5. Catch the All Link Report if we can (again if group number is right) do
       nothing
    6. If an ACK to the scene command is received, declare success.
    7. Otherwise, send direct commands to the devices that still remain in
       the dev_list

    As a result, it is recommended to set num_retry=1 for this handler.  Any
    failure of this command will results in the above handling of the scene
    command, whether it is caused by a NAK or a timeout.  Otherwise, if a
    single device fails to properly NAK a command (such as if a device has
    been removed from your network) an extremely long scene command will be
    sent up to three times using a lot of network resources.
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
                    It is recommended to set this to num_retry=1 for
                    ModemScene commands and let the automatic cleanup discussed
                    above handle any failures.
        """
        super().__init__(on_done, num_retry)

        self.modem = modem
        self.msg = msg
        self.dev_list = []
        for element in modem.db.find_group(msg.group):
            self.dev_list.append(element.addr)

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
                # This isn't the right group, so don't remove from list
                # but extend the waiting time to see if we get more
                self.update_expire_time()
                return Msg.UNKNOWN
            else:
                # Remove this from dev_list of it exists
                try:
                    self.dev_list.remove(msg.from_addr)
                except ValueError:
                    pass

                # Trigger an update of our internal state of this device
                device = self.modem.find(msg.from_addr)
                if device:
                    LOG.debug("%s broadcast to %s for group %s was ack'd",
                              self.modem.label, device.addr, msg.group)
                    device.handle_group_cmd(self.modem.addr, self.msg)
                else:
                    LOG.warning("%s broadcast - ack for device %s not found",
                                self.modem.label, msg.from_addr)

                if len(self.dev_list) == 0:
                    LOG.debug("All ACKs of Scene Command grp: %s received.",
                              msg.group)
                    self.on_done(True, "Scene command complete", None)
                    return Msg.FINISHED
                else:
                    return Msg.CONTINUE

        # This is an all link failure report.
        elif isinstance(msg, Msg.InpAllLinkFailure):
            if msg.group != self.msg.group:
                # This isn't the right group, so don't report anything
                # but extend the waiting time to see if we get more
                self.update_expire_time()
                return Msg.UNKNOWN
            else:
                LOG.error("%s failed to respond to broadcast for group %s",
                          msg.addr, msg.group)
                return Msg.CONTINUE

        # This is a NAK response from a device.
        elif (isinstance(msg, Msg.InpStandard) and
              msg.flags.type == Flags.Type.CLEANUP_NAK):
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
                #self.on_done(False, "Scene command failed", None)
                LOG.warning("Received NAK, waiting instead")
                #self._send_direct_cmds()
                return Msg.CONTINUE

            return Msg.FINISHED

        return Msg.UNKNOWN

    # Need to handle timeout too, make sure only call _send_direct_cmds once?

    #-----------------------------------------------------------------------
    def _send_direct_cmds(self):
        """If Scene Command Not ACK'd Properly, Send Direct Commands.

        Will cause direct commands to be send to each device to put the device
        in the appropriate state based on its db entry for the scene
        """
        for addr in self.dev_list:
            device = self.modem.find(addr)
            if device:
                LOG.ui("Sending Direct")
                device.send_direct_cleanup(self.msg, self)
            else:
                LOG.warning("Scene cleanup - device %s not found",
                            addr)
    #-----------------------------------------------------------------------
