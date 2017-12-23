#===========================================================================
#
# FanLinc device module.
#
#===========================================================================
import enum
import functools
from .Dimmer import Dimmer
from .. import handler
from .. import log
from .. import message as Msg
from ..Signal import Signal

LOG = log.get_logger()


class FanLinc(Dimmer):
    """TODO: doc
    """

    class Speed(enum.IntEnum):
        OFF = 0x00
        LOW = 0x3a   # range 0x01-0x7f - arbitrarily picked the mid point
        MED = 0xbf   # range 0x80-0xfe - arbitrarily picked the mid point
        HIGH = 0xff
        ON = -0x01   # turn on at last known speed

    def __init__(self, protocol, modem, address, name=None):
        """TODO: doc
        """
        super().__init__(protocol, modem, address, name)

        # Current fan speed.  We also store the last speed so that a
        # generic "on" command will use the last non-off speed that
        # was seen.  Note that ON is not a valid entry of _fan_speed.
        self._fan_speed = FanLinc.Speed.OFF
        self._last_speed = None

        # Support fan speed signals
        self.signal_fan_changed = Signal()  # (Device, Speed)

        self.cmd_map.update({
            'fan_on' : self.fan_on,
            'fan_off' : self.fan_off,
            'fan_set' : self.fan_set,
            })

    #-----------------------------------------------------------------------
    def pair(self, on_done=None):
        """Pair the device with the modem.

        This only needs to be called one time.  It will set the device
        as a controller and the modem as a responder so the modem will
        see group broadcasts and report them to us.

        The device must already be a responder to the modem (push set
        on the modem, then set on the device) so we can update it's
        database.
        """
        LOG.info("FanLinc %s pairing", self.addr)

        # Search our db to see if we have controller links for group 2
        # which is the fan speed control back to the modem.  If one
        # doesn't exist, add it on our device and the modem.
        group = 2
        if not self.db.find(self.modem.addr, group, True):
            LOG.ui("FanLinc adding ctrl for group %s", group)
            self.db_add_ctrl_of(self.modem.addr, group)
        else:
            LOG.ui("FanLinc ctrl for group %s already exists", group)

        # TODO: for a devices, check other end of the link -
        # i.e. check the device and the modem.  This is especially a
        # problem for battery devices which won't respond when asleep.

        # Call the dimmer base class to add links for group 1.
        super().pair(on_done=on_done)

    #-----------------------------------------------------------------------
    def refresh(self, force=False, on_done=None):
        """TODO doc
        """
        # Send a 0x19 0x03 command to get the fan speed level.
        LOG.info("Device %s cmd: fan status refresh", self.addr)

        # This sends a refresh ping which will respond w/ the fan
        # level and current database delta field.  The handler checks
        # that against the current value.  If it's different, it will
        # send a database download command to the device to update the
        # database.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x03)
        msg_handler = handler.DeviceRefresh(self, self.handle_fan_refresh,
                                            force=False, on_done=None,
                                            num_retry=3)
        self.protocol.send(msg, msg_handler)

        # Get the light level state.
        super().refresh(force, on_done=on_done)

    #-----------------------------------------------------------------------
    def fan_on(self, speed=None, on_done=None):
        """TODO: doc
        """
        assert isinstance(speed, FanLinc.Speed)

        if speed == FanLinc.Speed.ON or speed is None:
            if self._last_speed is not None:
                speed = self._last_speed
            else:
                speed = FanLinc.Speed.MED

        # Send an on command.  The fan control is done via extended
        # message with the first byte set as 0x02 per the fanlinc
        # developers guide.
        cmd1 = 0x11
        data = bytes([0x02] + [0x00] * 13)
        msg = Msg.OutExtended.direct(self.addr, cmd1, int(speed), data)

        # Use the standard command handler which will notify us when
        # the command is ACK'ed.
        callback = functools.partial(self.handle_speed_ack, on_done=on_done)
        msg_handler = handler.StandardCmd(msg, callback)

        # Send the message to the PLM modem for protocol.
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def fan_off(self, on_done=None):
        """TODO: doc

        This will send the command to the device to update it's state.
        When we get an ACK of the result, we'll change our internal
        state and emit the state changed signals.

        """
        LOG.info("Fan %s cmd: off", self.addr)

        # Send an on command.  The fan control is done via extended
        # message with the first byte set as 0x02 per the fanlinc
        # developers guide.
        cmd1 = 0x13
        data = bytes([0x02] + [0x00] * 13)
        msg = Msg.OutExtended.direct(self.addr, cmd1, 0x00, data)

        # Use the standard command handler which will notify us when
        # the command is ACK'ed.
        callback = functools.partial(self.handle_speed_ack, on_done=on_done)
        msg_handler = handler.StandardCmd(msg, callback)

        # Send the message to the PLM modem for protocol.
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def fan_set(self, speed, on_done=None):
        """TODO: docSet the device on or off.

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
        assert isinstance(speed, FanLinc.Speed)

        if speed != FanLinc.Speed.OFF:
            self.fan_on(speed, on_done=on_done)
        else:
            self.fan_off(on_done=on_done)

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
        # NOTE: the fan linc shouldn't be able to initialize a
        # broadcast message.  That's for actuators (switches, motion
        # sensors, etc) to trigger other things to occur.  Since the
        # fan linc is just a responder to other commands, that
        # shouldn't occur.
        LOG.error("FanLinc unexpected handle_broadcast called: %s", msg)
        super.handle_broadcast(msg)

    #-----------------------------------------------------------------------
    def handle_fan_refresh(self, msg):
        """Handle replies to the refresh command.

        The refresh command reply will contain the current fan level
        state in cmd2 and this updates the device with that value.

        Args:
          msg:  (message.InpStandard) The refresh message reply.  The current
                device state is in the msg.cmd2 field.
        """
        # NOTE: This is called by the handler.DeviceRefresh class when
        # the refresh message send by Base.refresh is ACK'ed.
        LOG.ui("Fan %s refresh speed at %s", self.addr, msg.cmd2)

        # Current fan speed is stored in cmd2 so update our speed to
        # match.
        self._set_fan_speed(msg.cmd2)

    #-----------------------------------------------------------------------
    def handle_speed_ack(self, msg, on_done=None):
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
            LOG.debug("FanLinc fan %s ACK: %s", self.addr, msg)
            self._set_fan_speed(msg.cmd2)
            if on_done:
                s = "Fan %s state updated to %s" % (self.addr, self._fan_speed)
                on_done(True, s, msg.cmd2)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("FanLinc fan %s NAK error: %s", self.addr, msg)
            if on_done:
                on_done(False, "Fan %s state update failed", None)

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
        # Group 1 is for the dimmer - pass that to the base class:
        if msg.group == 1:
            super().handle_group_cmd(addr, msg)
            return

        # Make sure we're really a responder to this message.  This
        # shouldn't ever occur.
        entry = self.db.find(addr, msg.group, is_controller=False)
        if not entry:
            LOG.error("FanLinc %s has no group %s entry from %s", self.addr,
                      msg.group, addr)
            return

        cmd = msg.cmd1

        # 0x11: on, speed in cmd2
        if cmd == 0x11:
            self._set_fan_speed(msg.cmd2)

        # 0x13: off
        elif cmd == 0x13:
            self._set_fan_speed(0x00)

        else:
            LOG.warning("FanLink %s unknown group cmd %#04x", self.addr, cmd)

    #-----------------------------------------------------------------------
    def _set_fan_speed(self, speed_level):
        """Set the device level state.

        This will change the internal state and emit the state changed
        signals.

        Args:
          speed_level:   todo:
        """
        LOG.info("Setting device %s on %s", self.label, speed_level)

        self._fan_speed = FanLinc.Speed.OFF

        if 0x01 <= speed_level <= 0x7f:
            self._fan_speed = FanLinc.Speed.LOW

        elif 0x80 <= speed_level <= 0xfe:
            self._fan_speed = FanLinc.Speed.MED

        elif speed_level == 0xff:
            self._fan_speed = FanLinc.Speed.HIGH

        # Record the last non-off speed as well.
        if self._fan_speed != FanLinc.Speed.OFF:
            self._last_speed = self._fan_speed

        self.signal_fan_changed.emit(self, self._fan_speed)

    #-----------------------------------------------------------------------
