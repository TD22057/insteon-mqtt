#===========================================================================
#
# Dimmer device module.  Used for anything that acts like a dimmer
# including wall switches, lamp modules, and some remotes.
#
#===========================================================================
import logging
from .Base import Base
from .. import handler
from .. import message as Msg
from .. import Signal

LOG = logging.getLogger(__name__)


class Dimmer(Base):
    """Insteon dimmer device.

    This includes any device that acts like a dimmer including wall
    switches, lamp modules, and some remotes.

    The Signal Dimmer.signal_level_changed will be emitted whenever
    the device level is changed with the calling sequence (device,
    level) where level is 0->0xff.
    """
    def __init__(self, protocol, modem, address, name):
        """Constructor

        Args:
           protocol:    (Protocol) The Protocol object used to communicate
                        with the Insteon network.  This is needed to allow
                        the device to send messages to the PLM modem.
           address:     (Address) The address of the device.
           name         (str) Nice alias name to use for the device.
        """
        Base.__init__(self, protocol, modem, address, name)

        # Current dimming level.
        self._level = None

        # Signal any change to the dimming level.  Calling sequence is
        # emit(Dimmer, leveL)
        self.signal_level_changed = Signal.Signal()

    #-----------------------------------------------------------------------
    def pair(self):
        """Pair the device with a PLM modem.

        This will add a link from the modem to and from the device
        (bi-directional pairing) and update the device databases both
        in memory and on the devices themselves.

        This only needs to be called one time when the device is first
        added to the network.

        Args:
           modem:  (Modem) The modem object to pair with.
        """
        # TODO: pair with modem
        pass

    #-----------------------------------------------------------------------
    def on(self, level=0xFF, instant=False):
        LOG.info("Dimmer %s cmd: on %s", self.addr, level)
        assert level >= 0 and level <= 0xff

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
        LOG.info("Dimmer %s cmd: off", self.addr)

        # Send an off or instant off command.
        cmd1 = 0x13 if not instant else 0x21
        msg = Msg.OutStandard.direct(self.addr, cmd1, 0x00)

        # Use the standard command handler which will notify us when
        # the command is ACK'ed.
        msg_handler = handler.StandardCmd(msg, self.handle_ack)

        # Send the message to the PLM modem for protocol.
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def incrementUp(self):
        LOG.info("Dimmer %s cmd: increment up", self.addr)

        msg = Msg.OutStandard.direct(self.addr, 0x15, 0x00)
        msg_handler = handler.StandardCmd(msg, self.handle_ack)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def incrementDown(self):
        LOG.info("Dimmer %s cmd: increment down", self.addr)

        msg = Msg.OutStandard.direct(self.addr, 0x16, 0x00)
        msg_handler = handler.StandardCmd(msg, self.handle_ack)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def manualStartUp(self):
        LOG.info("Dimmer %s cmd: manual start up", self.addr)

        msg = Msg.OutStandard.direct(self.addr, 0x17, 0x01)
        msg_handler = handler.StandardCmd(msg, self.handle_ack)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def manualStartDown(self):
        LOG.info("Dimmer %s cmd: manual start down", self.addr)

        msg = Msg.OutStandard.direct(self.addr, 0x17, 0x00)
        msg_handler = handler.StandardCmd(msg, self.handle_ack)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def manualStop(self):
        LOG.info("Dimmer %s cmd: manual stop", self.addr)

        msg = Msg.OutStandard.direct(self.addr, 0x18, 0x00)
        msg_handler = handler.StandardCmd(msg, self.handle_ack)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set(self, active, level=0xFF, instant=False):
        if active:
            self.on(level, instant)
        else:
            self.off(instant)

    #-----------------------------------------------------------------------
    def is_on(self):
        return not self._level

    #-----------------------------------------------------------------------
    def level(self):
        return self._level

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        # ACK of the broadcast - ignore this.
        if msg.cmd1 == 0x06:
            LOG.info("Dimmer %s broadcast ACK grp: %s", self.addr, msg.group)
            return

        # On command.  How do we tell the level?  It's not in the
        # message anywhere.
        elif msg.cmd1 == 0x11:
            LOG.info("Dimmer %s broadcast ON grp: %s", self.addr, msg.group)
            self._set_level(0xff)

        # Off command.
        elif msg.cmd1 == 0x13:
            LOG.info("Dimmer %s broadcast OFF grp: %s", self.addr, msg.group)
            self._set_level(0x00)

        # Call handle_broadcast for any device that we're the
        # controller of.
        Base.handle_broadcast(self, msg)

    #-----------------------------------------------------------------------
    def handle_ack(self, msg):
        LOG.debug("Dimmer %s ack message: %s", self.addr, msg)
        if msg.flags.type == Msg.Flags.DIRECT_ACK:
            self._set_level(msg.cmd2)

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        LOG.debug("Dimmer %s refresh message: %s", self.addr, msg)

        # Current dimmer level is stored in cmd2 so update our level
        # to match.
        self._set_level(msg.cmd2)

        # See if the database is up to date.
        Base.handle_refresh(self, msg)

    #-----------------------------------------------------------------------
    def handle_group_cmd(self, addr, msg):
        entry = self.db.find(addr, msg.group, 'RESP')
        if not entry:
            LOG.error("Dimmer %s has no group %s entry from %s", self.addr,
                      msg.group, addr)
            return

        cmd = msg.cmd1

        # 0x11: on, 0x12: on fast
        if cmd == 0x11 or cmd == 0x12:
            self._set_level(entry.on_level)

        # 0x13: off, 0x14: off fast
        elif cmd == 0x13 or cmd == 0x14:
            self._set_level(0x00)

        # Increment up (32 steps)
        elif cmd == 0x15:
            self._set_level(max(0xff, self._level + 8))

        # Increment down
        elif cmd == 0x16:
            self._set_level(min(0x00, self._level - 8))

        else:
            LOG.warning("Dimmer %s unknown group cmd %#04x", self.addr, cmd)

    #-----------------------------------------------------------------------
    def run_command(self, **kwargs):
        # TODO: handle new command

        LOG.info("Dimmer command: %s", kwargs)
        if 'level' in kwargs:
            level = int(kwargs.pop('level'))
            instant = bool(kwargs.pop('instant', False))
            if level == 0:
                self.off(instant)
            else:
                self.on(level, instant)

        elif 'increment' in kwargs:
            dir = kwargs.pop('increment')
            if dir == +1:
                self.incrementUp()
            elif dir == -1:
                self.incrementDown()
            else:
                LOG.error("Invalid increment %s", dir)

        else:
            Base.run_command(self, **kwargs)

    #-----------------------------------------------------------------------
    def _set_level(self, level):
        LOG.info("Setting device %s '%s' level %s", self.addr, self.name, level)
        self._level = level
        self.signal_level_changed.emit(self, self._level)

    #-----------------------------------------------------------------------
