#===========================================================================
#
# FanLinc device module.
#
#===========================================================================
import enum
from .Dimmer import Dimmer
from ..CommandSeq import CommandSeq
from .. import handler
from .. import log
from .. import message as Msg
from ..Signal import Signal

LOG = log.get_logger()


class FanLinc(Dimmer):
    """TODO: doc
    """
    type_name = "fan_linc"

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

        # Build a sequence of calls to the do the pairing.  This insures each
        # call finishes and works before calling the next one.  We have to do
        # this for device db manipulation because we need to know the memory
        # layout on the device before making changes.
        seq = CommandSeq(self.protocol, "FanLinc paired", on_done)

        # Start with a refresh command - since we're changing the db, it must
        # be up to date or bad things will happen.
        seq.add(self.refresh)

        # Add the device as a responder to the modem on group 1.  This is
        # probably already there - and maybe needs to be there before we can
        # even issue any commands but this check insures that the link is
        # present on the device and the modem.
        seq.add(self.db_add_resp_of, 0x01, self.modem.addr, 0x01,
                refresh=False)

        # Now add the device as the controller of the modem for groups 1
        # (dimmer) and 2 (fan).
        seq.add(self.db_add_ctrl_of, 0x01, self.modem.addr, 0x01,
                refresh=False)
        seq.add(self.db_add_ctrl_of, 0x02, self.modem.addr, 0x02,
                refresh=False)

        # Finally start the sequence running.  This will return so the
        # network event loop can process everything and the on_done callbacks
        # will chain everything together.
        seq.run()

    #-----------------------------------------------------------------------
    def refresh(self, force=False, on_done=None):
        """TODO doc
        """
        # Send a 0x19 0x03 command to get the fan speed level.
        LOG.info("Device %s cmd: fan status refresh", self.addr)

        seq = CommandSeq(self.protocol, "Refresh complete", on_done)

        # This sends a refresh ping which will respond w/ the fan
        # level and current database delta field.  Pass skip_db here - we'll
        # let the dimmer refresh handler above take care of getting the
        # database updated.  Otherwise this handler and the one created in
        # the dimmer refresh would download the database twice.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x03)
        msg_handler = handler.DeviceRefresh(self, self.handle_fan_refresh,
                                            force=False, num_retry=3,
                                            skip_db=True)
        seq.add_msg(msg, msg_handler)

        # If we get the FAN state correctly, then have the dimmer also get
        # it's state and update the database if necessary.
        seq.add(Dimmer.refresh, self, force)

        seq.run()

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
        msg_handler = handler.StandardCmd(msg, self.handle_speed_ack,
                                          on_done, num_retry=3)

        # Send the message to the PLM modem for protocol.
        self.send(msg, msg_handler)

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
        msg_handler = handler.StandardCmd(msg, self.handle_speed_ack,
                                          on_done)

        # Send the message to the PLM modem for protocol.
        self.send(msg, msg_handler)

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
            LOG.error("FanLinc fan %s NAK error: %s, Message: %s", self.addr,
                      msg.nak_str(), msg)
            if on_done:
                on_done(False, "Fan %s state update failed. " + msg.nak_str(),
                        None)

    #-----------------------------------------------------------------------
    def handle_group_cmd(self, addr, msg):
        """Respond to a group command for this device.

        This is called when this device is a responder to a scene.
        The device should look up the responder entry for the group in
        it's all link database and update it's state accordingly.

        Args:
          addr:  (Address) The device that sent the message.  This is the
                 controller in the scene.
          msg:   (InptStandard) Broadcast message from the device.  Use
                 msg.group to find the group and msg.cmd1 for the command.
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

        # 0x11: on
        if msg.cmd1 == 0x11:
            self._set_fan_speed(entry.data[0])

        # 0x13: off
        elif msg.cmd1 == 0x13:
            self._set_fan_speed(0x00)

        else:
            LOG.warning("FanLink %s unknown group cmd %#04x", self.addr,
                        msg.cmd1)

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
