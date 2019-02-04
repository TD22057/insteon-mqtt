#===========================================================================
#
# Insteon on/off outlet
#
#===========================================================================
import functools
from .Base import Base
from ..CommandSeq import CommandSeq
from .. import handler
from .. import log
from .. import message as Msg
from .. import on_off
from ..Signal import Signal
from .. import util

LOG = log.get_logger()


class Outlet(Base):
    """Insteon on/off outlet device.

    This is used for in-wall on/off outlets.  Each outlet (top and bottom) is
    an independent switch and is controlled via group 1 (top) and group2
    (bottom) inputs.

    The Signal Outlet.signal_active will be emitted whenever
    the device level is changed with the calling sequence (device,
    group, on) where on is True for on and False for off.
    """

    def __init__(self, protocol, modem, address, name=None):
        """Constructor

          protocol:    (Protocol) The Protocol object used to communicate
                       with the Insteon network.  This is needed to allow
                       the device to send messages to the PLM modem.
          modem:       (Modem) The Insteon modem used to find other devices.
          address:     (Address) The address of the device.
          name         (str) Nice alias name to use for the device.
        """
        super().__init__(protocol, modem, address, name)

        self._is_on = [False, False]  # top outlet, bottom outlet

        # Support on/off style signals.
        # API: func(Device, int group, bool is_on, on_off.Mode mode)
        self.signal_active = Signal()

        # Remove (mqtt) commands mapped to methods calls.  Add to the
        # base class defined commands.
        self.cmd_map.update({
            'on' : self.on,
            'off' : self.off,
            'set' : self.set,
            'scene' : self.scene,
            'set_flags' : self.set_flags,
            })

        # Special callback to run when receiving a broadcast clean up.  See
        # scene() for details.
        self.broadcast_done = None

        # NOTE: the outlet does NOT include the group in the ACK of an on/off
        # command.  So there is no way to tell which outlet is being ACK'ed
        # if we send multiple messages to it.  Each time on or off is called,
        # it pushes the outlet to this list so that when the ACK/NAK arrives,
        # we can pop it off and know which outlet was being commanded.
        self._which_outlet = []

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
        LOG.info("Outlet %s pairing", self.addr)

        # Build a sequence of calls to the do the pairing.  This insures each
        # call finishes and works before calling the next one.  We have to do
        # this for device db manipulation because we need to know the memory
        # layout on the device before making changes.
        seq = CommandSeq(self.protocol, "Outlet paired", on_done)

        # Start with a refresh command - since we're changing the db, it must
        # be up to date or bad things will happen.
        seq.add(self.refresh)

        # Add the device as a responder to the modem for group 1 and 2.  This
        # is probably already there - and maybe needs to be there before we
        # can even issue any commands but this check insures that the link is
        # present on the device and the modem.  Group 2 is required to
        # control the outlet
        for group in [1, 2]:
            seq.add(self.db_add_resp_of, group, self.modem.addr, 0x01,
                    refresh=False)

        # Now add the device as the controller of the modem for group 1 and
        # 2.  This lets the modem receive updates about the button presses
        # and state changes.
        for group in [1, 2]:
            seq.add(self.db_add_ctrl_of, group, self.modem.addr, group,
                    refresh=False)

        # Finally start the sequence running.  This will return so the
        # network event loop can process everything and the on_done callbacks
        # will chain everything together.
        seq.run()

    #-----------------------------------------------------------------------
    def refresh(self, force=False, on_done=None):
        """Refresh the current device state and database if needed.

        This sends a ping to the device.  The reply has the current
        device state (on/off, level, etc) and the current db delta
        value which is checked against the current db value.  If the
        current db is out of date, it will trigger a download of the
        database.

        This will send out an updated signal for the current device
        status whenever possible (like dimmer levels).

        Args:
          force:    If true, will force a refresh of the device
                    database even if the delta value matches
          on_done:  Optional callback run when the commands are finished.
        """
        LOG.info("Outlet %s cmd: status refresh", self.label)

        # This sends a refresh ping which will respond w/ the current
        # database delta field.  The handler checks that against the
        # current value.  If it's different, it will send a database
        # download command to the device to update the database.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x01)
        msg_handler = handler.DeviceRefresh(self, self.handle_refresh, force,
                                            on_done, num_retry=3)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def on(self, group=0x01, level=None, mode=on_off.Mode.NORMAL,
           on_done=None):
        """Turn the device on.

        This will send the command to the device to update it's state.
        When we get an ACK of the result, we'll change our internal
        state and emit the state changed signals.

        TODO: doc
        Args:
          instant:  (bool) False for a normal ramping change, True for an
                    instant change.
        """
        LOG.info("Outlet %s grp: %s cmd: on", group, self.addr)
        assert 1 <= group <= 2
        assert level >= 0 and level <= 0xff
        assert isinstance(mode, on_off.Mode)

        # Send the requested on code value.
        cmd1 = on_off.Mode.encode(True, mode)

        # Top outlet uses a standard message
        if group == 1:
            msg = Msg.OutStandard.direct(self.addr, cmd1, 0xff)

        # Bottom outlet uses an extended message
        else:
            data = bytes([0x02] + [0x00] * 13)
            msg = Msg.OutExtended.direct(self.addr, cmd1, 0xff, data)

        # Use the standard command handler which will notify us when
        # the command is ACK'ed.
        msg_handler = handler.StandardCmd(msg, self.handle_ack, on_done)

        # See __init__ code comments for what this is for.
        self._which_outlet.append(group)

        # Send the message to the PLM modem for protocol.
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def off(self, group=0x01, mode=on_off.Mode.NORMAL, on_done=None):
        """Turn the device off.

        This will send the command to the device to update it's state.
        When we get an ACK of the result, we'll change our internal
        state and emit the state changed signals.

        Args:
          instant:  (bool) False for a normal ramping change, True for an
                    instant change.
        """
        LOG.info("Outlet %s cmd: off", self.addr)
        assert 1 <= group <= 2
        assert isinstance(mode, on_off.Mode)

        # Send the correct off code.
        cmd1 = on_off.Mode.encode(False, mode)

        # Top outlet uses a standard message
        if group == 1:
            msg = Msg.OutStandard.direct(self.addr, cmd1, 0x00)

        # Bottom outlet uses an extended message
        else:
            data = bytes([0x02] + [0x00] * 13)
            msg = Msg.OutExtended.direct(self.addr, cmd1, 0x00, data)

        # Use the standard command handler which will notify us when
        # the command is ACK'ed.
        msg_handler = handler.StandardCmd(msg, self.handle_ack, on_done)

        # See __init__ code comments for what this is for.
        self._which_outlet.append(group)

        # Send the message to the PLM modem for protocol.
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set(self, level, group=0x01, mode=on_off.Mode.NORMAL, on_done=None):
        """Set the device on or off.

        This will send the command to the device to update it's state.
        When we get an ACK of the result, we'll change our internal
        state and emit the state changed signals.

        Args:
          level:    (int/bool) If non zero, turn the device on.
        TODO
        """
        if level:
            self.on(group, level, mode, on_done)
        else:
            self.off(group, mode, on_done)

    #-----------------------------------------------------------------------
    def scene(self, is_on, group=0x01, on_done=None):
        """TODO: doc
        """
        LOG.info("Outlet %s scene %s", self.addr, "on" if is_on else "off")
        assert group == 0x01

        # Send an 0x30 all link command to simulate the button being pressed
        # on the outlet.  See page 163 of insteon dev guide
        cmd1 = 0x11 if is_on else 0x13
        data = bytes([
            group,  # D1 = group (button)
            0x00,   # D2 = use level in scene db
            0x00,   # D3 = on level if D2=0x01
            cmd1,   # D4 = cmd1 to send
            0x00,   # D5 = cmd2 to send
            0x00,   # D6 = use ramp rate in scene db
            ] + [0x00] * 8)
        msg = Msg.OutExtended.direct(self.addr, 0x30, 0x00, data)

        # Use the standard command handler which will notify us when
        # the command is ACK'ed.
        callback = on_done if is_on else None
        msg_handler = handler.StandardCmd(msg, self.handle_scene, callback)
        self.send(msg, msg_handler)

        # Scene triggering will not turn the device off (no idea why), so we
        # have to send an explicit off command to do that.  If this is None,
        # we're triggering a scene and so should bypass the normal
        # handle_broadcast logic to take this case into account.  Note that
        # if we sent and off command either before or after the ACK of the
        # command above, it doesn't work - we have to wait until the
        # broadcast msg is finished.
        if not is_on:
            self.broadcast_done = functools.partial(self.off, group=group,
                                                    on_done=on_done)

    #-----------------------------------------------------------------------
    def set_backlight(self, level, on_done=None):
        """TODO: doc

        NOTE: default factory backlight == 0x1f
        NOTE: only switches with LED display will do anything with this
              command.
        """
        LOG.info("Outlet %s setting backlight to %s", self.label, level)

        # Bound to 0x11 <= level <= 0xff per page 157 of insteon dev guide.
        level = max(0x11, min(level, 0xff))

        # Extended message data - see Insteon dev guide p156.
        data = bytes([
            0x01,   # D1 must be group 0x01
            0x07,   # D2 set global led brightness
            level,  # D3 brightness level
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when
        # the command is ACK'ed.
        msg_handler = handler.StandardCmd(msg, self.handle_backlight,
                                          on_done)

        # Send the message to the PLM modem for protocol.
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_flags(self, on_done, **kwargs):
        """TODO: doc
        valid kwargs:
           backlight: 0x11-0xff (factory default 0x1f)
        """
        LOG.info("Outlet %s cmd: set flags", self.label)

        # Check the input flags to make sure only ones we can understand were
        # passed in.
        flags = set(["backlight"])
        unknown = set(kwargs.keys()).difference(flags)
        if unknown:
            raise Exception("Unknown Outlet flags input: %s.\n Valid flags "
                            "are: %s" % unknown, flags)

        # FUTURE: to support other flags, use a CommandSeq
        backlight = util.input_byte(kwargs, "backlight")
        self.set_backlight(backlight, on_done)

    #-----------------------------------------------------------------------
    def handle_backlight(self, msg, on_done):
        """TODO: doc
        """
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            on_done(True, "Backlight level updated", None)
        else:
            on_done(False, "Backlight level failed", None)

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
            LOG.info("Outlet %s broadcast ACK grp: %s", self.addr, msg.group)
            if self.broadcast_done:
                self.broadcast_done()
            self.broadcast_done = None
            return

        # On/off command codes.
        elif on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)
            LOG.info("Outlet %s broadcast grp: %s on: %s mode: %s", self.addr,
                     msg.group, is_on, mode)

            if is_on:
                self._set_is_on(msg.group, True, mode)

            # If broadcast_done is active, this is a generated broadcast and
            # we need to manually turn the device off so don't update it's
            # state until that occurs.
            elif not self.broadcast_done:
                self._set_is_on(msg.group, False, mode)

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
        # From outlet developers guide - refresh must be 0x19 0x01 to enable
        # these codes.
        response = {
            0x00: [False, False],
            0x01: [True, False],
            0x02: [False, True],
            0x03: [True, True]
            }

        is_on = response.get(msg.cmd2, None)
        if is_on is None:
            LOG.error("Outlet %s unknown refresh response %s", self.label,
                      msg.cmd2)
            return

        LOG.ui(" %s refresh top=%s bottom=%s", self.label, is_on[0], is_on[1])

        # Set the state for each outlet.
        self._set_is_on(1, is_on[0])
        self._set_is_on(2, is_on[1])

    #-----------------------------------------------------------------------
    def handle_ack(self, msg, on_done):
        """Callback for standard commanded messages.

        This callback is run when we get a reply back from one of our
        commands to the device.  If the command was ACK'ed, we know it
        worked so we'll update the internal state of the device and
        emit the signals to notify others of the state change.

        Args:
          msg:  (message.InpStandard) The reply message from the device.
                The on/off level will be in the cmd2 field.
        """
        if not self._which_outlet:
            LOG.error("Outlet %s ACK error.  No outlet ID's were saved",
                      self.addr)
            on_done(False, "Outlet update failed - no ID's saved", None)
            return

        # See __init__ code comments for what this is for.
        group = self._which_outlet.pop(0)

        # If this it the ACK we're expecting, update the internal
        # state and emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("Outlet %s grp: %s ACK: %s", self.addr, group, msg)
            is_on, mode = on_off.Mode.decode(msg.cmd1)
            self._set_is_on(group, is_on, mode)
            on_done(True, "Outlet state updated to on=%s" % self._is_on,
                    self._is_on)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("Outlet %s NAK error: %s", self.addr, msg)
            on_done(False, "Outlet state update failed", None)

    #-----------------------------------------------------------------------
    def handle_scene(self, msg, on_done):
        """Callback for scene simulation commanded messages.

        This callback is run when we get a reply back from triggering a scene
        on the device.  If the command was ACK'ed, we know it worked.  The
        device will then send out standard broadcast messages which will
        trigger other updates for the scene devices.

        Args:
          msg:  (message.InpStandard) The reply message from the device.
        """
        # If this it the ACK we're expecting, update the internal
        # state and emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("Outlet %s ACK: %s", self.addr, msg)
            on_done(True, "Scene triggered", None)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("Outlet %s NAK error: %s", self.addr, msg)
            on_done(False, "Scene trigger failed failed", None)

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
        # Make sure we're really a responder to this message.  This
        # shouldn't ever occur.
        entry = self.db.find(addr, msg.group, is_controller=False)
        if not entry:
            LOG.error("Outlet %s has no group %s entry from %s", self.addr,
                      msg.group, addr)
            return

        if on_off.Mode.is_valid(msg.cmd1):
            is_on, mode = on_off.Mode.decode(msg.cmd1)
            self._set_is_on(msg.group, is_on, mode)
        else:
            LOG.warning("Outlet %s unknown group cmd %#04x", self.addr,
                        msg.cmd1)

    #-----------------------------------------------------------------------
    def _set_is_on(self, group, is_on, mode=on_off.Mode.NORMAL):
        """Set the device on/off state.

        This will change the internal state and emit the state changed
        signal.

        Args:
          is_on:   (bool) True if motion is active, False if it isn't.
        """
        is_on = bool(is_on)

        LOG.info("Setting device %s grp: %s on %s %s", self.label, group,
                 is_on, mode)
        self._is_on[group - 1] = is_on

        # Notify others that the outlet state has changed.
        self.signal_active.emit(self, group, is_on, mode)

    #-----------------------------------------------------------------------
