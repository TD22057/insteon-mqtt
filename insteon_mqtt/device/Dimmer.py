#===========================================================================
#
# Dimmer device module.  Used for anything that acts like a dimmer
# including wall switches, lamp modules, and some remotes.
#
#===========================================================================
from .Base import Base
from .. import handler
from .. import log
from .. import message as Msg
from ..Signal import Signal

LOG = log.get_logger()


class Dimmer(Base):
    """Insteon dimmer device.

    This includes any device that acts like a dimmer including wall
    switches, lamp modules, and some remotes.

    The Signal Dimmer.signal_level_changed will be emitted whenever
    the device level is changed with the calling sequence (device,
    level) where level is 0->0xff.

    Sample configuration input:

        insteon:
          devices:
            - dimmer:
              name: "Table lamp"
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
       set:      Argument 'level' = 0->255 to set brightness level.  Optional
                 arg 'instant' with value True or False to change state
                 instantly (default=False).
       up:       No arguments.  Increment the current dimmer level up.
       down:     No arguments.  Increment the current dimmer level down.
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

        # Current dimming level. 0x00 -> 0xff
        self._level = None

        # Support dimmer style signals and motion on/off style signals.
        self.signal_level_changed = Signal()  # (Device, level)

        # Remove (mqtt) commands mapped to methods calls.  Add to the
        # base class defined commands.
        self.cmd_map.update({
            'on' : self.on,
            'off' : self.off,
            'set' : self.set,
            'increment_up' : self.increment_up,
            'increment_down' : self.increment_down,
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
        LOG.info("Dimmer %s pairing", self.addr)

        # Search our db to see if we have controller links for group 1
        # back to the modem.  If one doesn't exist, add it on our
        # device and the modem.
        if not self.db.find(self.modem.addr, 1, True):
            LOG.info("Dimmer adding ctrl for group 1")
            self.db_add_ctrl_of(self.modem.addr, 1)

    #-----------------------------------------------------------------------
    def on(self, level=0xFF, instant=False):
        """Turn the device on.

        This will send the command to the device to update it's state.
        When we get an ACK of the result, we'll change our internal
        state and emit the state changed signals.

        Args:
          level:    (int) If non zero, turn the device on.  Should be
                    in the range 0x00 to 0xff.
          instant:  (bool) False for a normal ramping change, True for an
                    instant change.
        """
        LOG.info("Dimmer %s cmd: on %s", self.addr, level)
        assert level >= 0 and level <= 0xff
        if self._level == level:
            LOG.info("Dimmer %s '%s' is already on %s", self.addr, self.name,
                     level)
            return

        # Send an on or instant on command.
        cmd1 = 0x11 if not instant else 0x21
        msg = Msg.OutStandard.direct(self.addr, cmd1, level)

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
        LOG.info("Dimmer %s cmd: off", self.addr)
        if self._level == 0:
            LOG.info("Dimmer %s '%s' is already off", self.addr, self.name)
            return

        # Send an off or instant off command.
        cmd1 = 0x13 if not instant else 0x21
        msg = Msg.OutStandard.direct(self.addr, cmd1, 0x00)

        # Use the standard command handler which will notify us when
        # the command is ACK'ed.
        msg_handler = handler.StandardCmd(msg, self.handle_ack)

        # Send the message to the PLM modem for protocol.
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def increment_up(self):
        """Increment the current level up.

        Levels increment in usits of 32 (8 divisions from off to on).

        This will send the command to the device to update it's state.
        When we get an ACK of the result, we'll change our internal
        state and emit the state changed signals.
        """
        LOG.info("Dimmer %s cmd: increment up", self.addr)

        msg = Msg.OutStandard.direct(self.addr, 0x15, 0x00)
        msg_handler = handler.StandardCmd(msg, self.handle_ack)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def increment_down(self):
        """Increment the current level down.

        Levels increment in usits of 32 (8 divisions from off to on).

        This will send the command to the device to update it's state.
        When we get an ACK of the result, we'll change our internal
        state and emit the state changed signals.
        """
        LOG.info("Dimmer %s cmd: increment down", self.addr)

        msg = Msg.OutStandard.direct(self.addr, 0x16, 0x00)
        msg_handler = handler.StandardCmd(msg, self.handle_ack)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set(self, level, instant=False):
        """Set the device on or off.

        This will send the command to the device to update it's state.
        When we get an ACK of the result, we'll change our internal
        state and emit the state changed signals.

        Args:
          level:    (int/bool) If non zero, turn the device on.  Should be
                    in the range 0x00 to 0xff.  If True, the level will be
                    0xff.
          instant:  (bool) False for a normal ramping change, True for an
                    instant change.
        """
        if level:
            if level is True:
                level = 0xff

            self.on(level, instant)
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
        cmd = msg.cmd1

        # ACK of the broadcast - ignore this.
        if cmd == 0x06:
            LOG.info("Dimmer %s broadcast ACK grp: %s", self.addr, msg.group)
            return

        # On command.  How do we tell the level?  It's not in the
        # message anywhere.
        elif cmd == 0x11:
            LOG.info("Dimmer %s broadcast ON grp: %s", self.addr, msg.group)
            self._set_level(0xff)

        # Off command.
        elif cmd == 0x13:
            LOG.info("Dimmer %s broadcast OFF grp: %s", self.addr, msg.group)
            self._set_level(0x00)

        # Starting manual increment (cmd2 0x00=up, 0x01=down)
        elif cmd == 0x17:
            LOG.info("Dimmer %s starting manual change %s", self.addr,
                     "UP" if msg.cmd2 == 0x00 else "DN")

        # Stopping manual increment (cmd2 = unused)
        elif cmd == 0x18:
            LOG.info("Dimmer %s stopping manual change", self.addr)

            # Ping the light to get the new level
            self.refresh()

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
        LOG.debug("Dimmer %s refresh message: %s", self.addr, msg)

        # Current dimmer level is stored in cmd2 so update our level
        # to match.
        self._set_level(msg.cmd2)

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
            LOG.debug("Dimmer %s ACK: %s", self.addr, msg)
            self._set_level(msg.cmd2)

        elif msg.flags.Dimmer == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("Dimmer %s NAK error: %s", self.addr, msg)

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
            LOG.error("Dimmer %s has no group %s entry from %s", self.addr,
                      msg.group, addr)
            return

        cmd = msg.cmd1

        # 0x11: on, 0x12: on fast
        if cmd in Dimmer.on_codes:
            self._set_level(entry.data[0])

        # 0x13: off, 0x14: off fast
        elif cmd in Dimmer.off_codes:
            self._set_level(0x00)

        # Increment up (32 steps)
        elif cmd == 0x15:
            self._set_level(max(0xff, self._level + 8))

        # Increment down
        elif cmd == 0x16:
            self._set_level(min(0x00, self._level - 8))

        # Starting manual increment (cmd2 0x00=up, 0x01=down)
        elif cmd == 0x17:
            pass

        # Stopping manual increment (cmd2 = unused)
        elif cmd == 0x18:
            # Ping the light to get the new level
            self.refresh()

        else:
            LOG.warning("Dimmer %s unknown group cmd %#04x", self.addr, cmd)

    #-----------------------------------------------------------------------
    def _set_level(self, level):
        """Set the device level state.

        This will change the internal state and emit the state changed
        signals.

        Args:
          level:   (int) 0x00 for off, 0xff for 100%.
        """
        LOG.info("Setting device %s '%s' on %s", self.addr, self.name, level)
        self._level = level

        self.signal_level_changed.emit(self, level)

    #-----------------------------------------------------------------------
