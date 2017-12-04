#===========================================================================
#
# Insteon on/off device
#
#===========================================================================
from .Base import Base
from .. import handler
from .. import log
from .. import message as Msg
from ..Signal import Signal

LOG = log.get_logger()


class Switch(Base):
    """Insteon on/off switch device.

    This includes any device that turns on and off like an appliance
    module or non-dimming lamp module.

    The Signal Switch.signal_active will be emitted whenever
    the device level is changed with the calling sequence (device,
    on) where on is True for on and False for off.

    Sample configuration input:

        insteon:
          devices:
            - switch:
              name: "Washing machine"
              address: 44.a3.79

    The run_command() method is used for arbitrary remote commanding
    (via MQTT for example).  The input is a dict (or keyword args)
    containing a 'cmd' key with the value as the command name and any
    additional arguments needed for the command as other key/value
    pairs. Valid commands for all devices are:

       getdb:    No arguments.  Download the PLM modem all link database
                 and save it to file.
       refresh:  No arguments.  Ping the device to get the current state and
                 see if the database is current.  Reloads the modem database
                 if needed.  This will emit the current state as a signal.
       on:       No arguments.  Turn the device on.
       off:      No arguments.  Turn the device off
       set:      Argument 'level' = 0->255 to set brightness level.  Any value
                 above 0 is treated as on.  Optional arg 'instant' with value
                 True or False to change state instantly (default=False).
    """
    on_codes = [0x11, 0x12, 0x21, 0x23]  # on, fast on, instant on, manual on
    off_codes = [0x13, 0x14, 0x22]  # off, fast off, instant off

    def __init__(self, protocol, modem, address, name=None):
        """Constructor

        Args:
          protocol:    (Protocol) The Protocol object used to communicate
                       with the Insteon network.  This is needed to allow
                       the device to send messages to the PLM modem.
          modem:       (Modem) The Insteon modem used to find other devices.
          address:     (Address) The address of the device.
          name         (str) Nice alias name to use for the device.
        """
        super().__init__(protocol, modem, address, name)

        self._is_on = False

        # Support on/off style signals.
        self.signal_active = Signal()  # (Device, bool)

        # Remove (mqtt) commands mapped to methods calls.  Add to the
        # base class defined commands.
        self.cmd_map.update({
            'on' : self.on,
            'off' : self.off,
            'set' : self.set,
            })

    #-----------------------------------------------------------------------
    def pair(self):
        """Pair the device with the modem.

        This only needs to be called one time.  It will set the device
        as a controller and the modem as a responder so the modem will
        see group broadcasts and report them to us.

        The device must already be a responder to the modem (push set
        on the modem, then set on the device) so we can update it's
        database.
        """
        LOG.info("Switch %s pairing", self.addr)

        # Search our db to see if we have controller links for group 1
        # back to the modem.  If one doesn't exist, add it on our
        # device and the modem.
        if not self.db.find(self.modem.addr, 1, True):
            LOG.info("Switch adding ctrl for group 1")
            self.db_add_ctrl_of(self.modem.addr, 1)

    #-----------------------------------------------------------------------
    def is_on(self):
        """Return if the device is on or not.
        """
        return self._is_on

    #-----------------------------------------------------------------------
    def on(self, instant=False):
        """Turn the device on.

        This will send the command to the device to update it's state.
        When we get an ACK of the result, we'll change our internal
        state and emit the state changed signals.

        Args:
          instant:  (bool) False for a normal ramping change, True for an
                    instant change.
        """
        LOG.info("Switch %s cmd: on", self.addr)
        if self._is_on:
            LOG.info("Device %s '%s' is already on", self.addr, self.name)
            return

        # Send an on or instant on command.
        cmd1 = 0x11 if not instant else 0x21
        msg = Msg.OutStandard.direct(self.addr, cmd1, 0xff)

        # Use the standard command handler which will notify us when
        # the command is ACK'ed.
        msg_handler = handler.StandardCmd(msg, self.handle_ack)

        # Send the message to the PLM modem for protocol.
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def off(self, instant=False):
        """Turn the device off.

        This will send the command to the device to update it's state.
        When we get an ACK of the result, we'll change our internal
        state and emit the state changed signals.

        Args:
          instant:  (bool) False for a normal ramping change, True for an
                    instant change.
        """
        LOG.info("Switch %s cmd: off", self.addr)
        if not self._is_on:
            LOG.info("Device %s '%s' is already off", self.addr, self.name)
            return

        # Send an off or instant off command.  Instant off is the same
        # command as instant on, just with the level set to 0x00.
        cmd1 = 0x13 if not instant else 0x21
        msg = Msg.OutStandard.direct(self.addr, cmd1, 0x00)

        # Use the standard command handler which will notify us when
        # the command is ACK'ed.
        msg_handler = handler.StandardCmd(msg, self.handle_ack)

        # Send the message to the PLM modem for protocol.
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set(self, level, instant=False):
        """Set the device on or off.

        This will send the command to the device to update it's state.
        When we get an ACK of the result, we'll change our internal
        state and emit the state changed signals.

        Args:
          level:    (int/bool) If non zero, turn the device on.
          instant:  (bool) False for a normal ramping change, True for an
                    instant change.
        """
        if level:
            self.on(instant)
        else:
            self.off(instant)

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        """Handle broadcast messages from this device.

        The broadcast message from a device is sent when the device is
        triggered.  The message has the group ID in it.  We'll update
        the device state and look up the group in the all link
        database.  For each device that is in the group (as a
        reponsder), we'll call handle_group_cmd() on that device to
        trigger it.  This way all the devices in the group are updated
        to the correct values when we see the broadcast message.

        Args:
          msg:   (InptStandard) Broadcast message from the device.
        """
        # ACK of the broadcast - ignore this.
        if msg.cmd1 == 0x06:
            LOG.info("Switch %s broadcast ACK grp: %s", self.addr, msg.group)
            return

        # On command.  0x11: on, 0x12: on fast
        elif msg.cmd1 in Switch.on_codes:
            LOG.info("Switch %s broadcast ON grp: %s", self.addr, msg.group)
            self._set_is_on(True)

        # Off command. 0x13: off, 0x14: off fast
        elif msg.cmd1 in Switch.off_codes:
            LOG.info("Switch %s broadcast OFF grp: %s", self.addr, msg.group)
            self._set_is_on(False)

        # This will find all the devices we're the controller of for
        # this group and call their handle_group_cmd() methods to
        # update their states since they will have seen the group
        # broadcast and updated (without sending anything out).
        super().handle_broadcast(msg)

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        """Handle replies to the refresh command.

        The refresh command reply will contain the current device
        state in cmd2 and this updates the device with that value.

        Args:
          msg:  (message.InpStandard) The refresh message reply.  The current
                device state is in the msg.cmd2 field.
        """
        LOG.debug("Switch %s refresh message: %s", self.addr, msg)

        # Current on/off level is stored in cmd2 so update our level
        # to match.
        self._set_is_on(msg.cmd2 > 0x00)

    #-----------------------------------------------------------------------
    def handle_ack(self, msg):
        """Callback for standard commanded messages.

        This callback is run when we get a reply back from one of our
        commands to the device.  If the command was ACK'ed, we know it
        worked so we'll update the internal state of the device and
        emit the signals to notify others of the state change.

        Args:
          msg:  (message.InpStandard) The reply message from the device.
                The on/off level will be in the cmd2 field.
        """
        # If this it the ACK we're expecting, update the internal
        # state and emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("Switch %s ACK: %s", self.addr, msg)
            self._set_is_on(msg.cmd2 > 0x00)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("Switch %s NAK error: %s", self.addr, msg)

    #-----------------------------------------------------------------------
    def handle_group_cmd(self, addr, msg):
        """Respond to a group command for this device.

        This is called when this device is a responder to a scene.
        The device should look up the responder entry for the group in
        it's all link database and update it's state accordingly.

        Args:
          addr:  (Address) The device that sent the message.  This is the
                 controller in the scene.
          msg:   (message.InpStandard) The broadcast message that was sent.
                 Use msg.group to find the scene group that was broadcast.
        """
        # Make sure we're really a responder to this message.  This
        # shouldn't ever occur.
        entry = self.db.find(addr, msg.group, is_controller=False)
        if not entry:
            LOG.error("Switch %s has no group %s entry from %s", self.addr,
                      msg.group, addr)
            return

        # 0x11: on, 0x12: on fast
        if msg.cmd1 in Switch.on_codes:
            self._set_is_on(True)

        # 0x13: off, 0x14: off fast
        elif msg.cmd1 in Switch.off_codes:
            self._set_is_on(False)

        else:
            LOG.warning("Switch %s unknown group cmd %#04x", self.addr,
                        msg.cmd1)

    #-----------------------------------------------------------------------
    def _set_is_on(self, is_on):
        """Set the device on/off state.

        This will change the internal state and emit the state changed
        signal.

        Args:
          is_on:   (bool) True if motion is active, False if it isn't.
        """
        LOG.info("Setting device %s '%s' on %s", self.addr, self.name, is_on)
        self._is_on = bool(is_on)

        # Notify others that the switch state has changed.
        self.signal_active.emit(self, self._is_on)

    #-----------------------------------------------------------------------
