#===========================================================================
#
# Insteon on/off device
#
#===========================================================================
import functools
from .Base import Base
from ..CommandSeq import CommandSeq
from .. import handler
from .. import log
from .. import message as Msg
from ..Signal import Signal
from .. import util

LOG = log.get_logger()


class IOLinc(Base):
    """Insteon IOLinc relay/sensor device.

    This class can be used to model the IOLinc device which has a sensor and
    a relay.  Unfortunately, it behaves very poorly.  Unlike every other
    device, it doesn't broadcast the relay and sensor on separate groups.  So
    messages arrive from either and commands are for the relay.  There a
    number of internal mode state which change how the device behaves (see
    below for details).

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).  Supported signals are:

    - signal_on_off( Device, bool is_on, on_off.Mode mode ):
      Sent whenever the sensor is turned on or off.

    - signal_manual( Device, on_off.Manual mode ): Sent when the device
      starts or stops manual mode (when a button is held down or released).

    NOTES:
    Link the relay as responder to another device (controller).  Acttivate
    the controller.  Relay updates but state update is NOT emitted.

    Latching mode:
      - Click set button by hand.  Toggles relay on or off.  But it also
        emits a status update for the relay, not the sensor.  [BAD]

      - Send on command.  Relay turns on.  No state update. [GOOD]
      - Send off command.  Relay turns on.  No state update. [GOOD]

      - Send scene simulation on command.  Relay turns on.  Status update
        with ON payload sent.  [BAD]
    - Send scene simulation Off command.  Relay turns off.  Status update
        with OFF payload sent.  [BAD]

      - Click controller button (or send modem scene) on.  Relay turns on.
        No state update.  [GOOD]
      - Click controller button (or send modem scene) off.  Relay turns
        off. No state update.  [GOOD]

    Momemtary A:
      ON turns relay on, then off after delay.  OFF is ignored.  (this can be
      reversed - depends on the state of the relay when paired - i.e D1 in
      the link db responder line)

      - Click set button by hand.  Relay turns on, then off.  Emits a state
        ON update but no OFF update.  [BAD]

      - Send on.  Relay turns on, then off after delay.  No state
        update. [GOOD]
      - Send off.  Relay does nothing.  No state update. [GOOD]

      - Send scene simulation on command.  Relay turns on, then off after
        delay.  Status update with ON payload sent. [BAD]
      - Send scene simulation Off command.  Nothing happens.

      - Click controller button (or send modem scene) on.  Relay turns on,
        then off after delay.  No state update.  [GOOD]
      - Click controller button (or send modem scene) off.  Nothing happens.

    Momentary B:
      ON or OFF turns relay on, then off after delay.

      - Click set button by hand.  Relay turns on, then off after delay.
        Emits a state ON update but no OFF update.  [BAD]

      - Send on.  Relay turns on, then off after delay.  No state
        update. [GOOD]
      - Send off.  Relay does nothing.  No state update. [GOOD]

      - Send scene simulation on command.  Relay turns on, then off after
        delay.  Status update with ON payload sent. [BAD]
      - Send scene simulation Off command.  Relay turns on, then off after
        delay.  Status update with OFF payload sent.  [BAD]

      - Click controller button (or send modem scene) on.  Relay turns on,
        then off after delay.  No state update.  [GOOD]
      - Click controller button (or send modem scene) off.  Relay turns on,
        then off after delay.  No state update.  [GOOD]

    Momentary C:
      ON turns relay on only if sensor is in correct state (state of device
      when linked - i.e. D1 in the link db responder line).

      - Click set button by hand.  Relay turns on, then off after delay.
        Emits a state ON update but no OFF update.  [BAD]

      - Send on.  Relay turns on, then off after delay.  No state
        update.  [GOOD] - But this ignores the sensor value [BAD?]
      - Send off.  Relay does nothing.  No state update. [GOOD]

      - Send scene simulation on command.  Relay turns on, then off after
        delay.  Status update with ON payload sent.  Ignores sensor value
        [BAD]
      - Send scene simulation Off command.  Relay turns on, then off after
        delay.  Status update with ON payload sent.  Ignores sensor value
        [BAD]

      - Click controller button (or send modem scene) on.  Relay turns on,
        then off after delay.  No state update.  [GOOD]  Sensor value is
        handled correctly.
      - Click controller button (or send modem scene) off.  Relay turns on,
        then off after delay.  No state update.  [GOOD]  Sensor value is
        handled correctly.

    Not about Momentary C: If you click a keypadlinc button, it will toggle.
    The IOLinc may not do anything though - i.e. if the sensor is already in
    that state, it won't fire.  But the keypad button has toggled so now it's
    LED on/off is wrong.  Might be some way to "fix" this but it's not
    obvious whether or not it's a good idea or not.  Might be nice to have an
    option to FORCE a controller of the IO linc to always be in the correct
    state to show the door open or closed.
    """
    type_name = "io_linc"

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

        # Support on/off style signals for the sensor
        # API: func(Device, bool is_on)
        self.signal_on_off = Signal()

        # Group number of the virtual modem scene linked to this device.  We
        # need this so we can trigger the device and have it respond using
        # the correct mode information.  If we used a direct command, it will
        # just turn on/off the relay and not use the various latching and
        # momentary configurations.  So instead of sending a direct on/off,
        # we'll trigger this virtual scene.
        self.modem_scene = None

        # Remote (mqtt) commands mapped to methods calls.  Add to the
        # base class defined commands.
        self.cmd_map.update({
            'on' : self.on,
            'off' : self.off,
            'set' : self.set,
            'scene' : self.scene,
            'set_flags' : self.set_flags,
            })

    #-----------------------------------------------------------------------
    def pair(self, on_done=None):
        """Pair the device with the modem.

        This only needs to be called one time.  It will set the device as a
        controller and the modem as a responder so the modem will see group
        broadcasts and report them to us.

        The device must already be a responder to the modem (push set on the
        modem, then set on the device) so we can update it's database.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("IOLinc %s pairing", self.addr)

        # Build a sequence of calls to the do the pairing.  This insures each
        # call finishes and works before calling the next one.  We have to do
        # this for device db manipulation because we need to know the memory
        # layout on the device before making changes.
        seq = CommandSeq(self.protocol, "IOLinc paired", on_done)

        # Start with a refresh command - since we're changing the db, it must
        # be up to date or bad things will happen.
        seq.add(self.refresh)

        # Add the device as a responder to the modem on group 1.  This is
        # probably already there - and maybe needs to be there before we can
        # even issue any commands but this check insures that the link is
        # present on the device and the modem.
        seq.add(self.db_add_resp_of, 0x01, self.modem.addr, 0x01,
                refresh=False)

        # Now add the device as the controller of the modem for group 1.
        # This lets the modem receive updates about the button presses and
        # state changes.
        seq.add(self.db_add_ctrl_of, 0x01, self.modem.addr, 0x01,
                refresh=False)

        # We need to create a virtual modem scene to trigger the IOLinc
        # properly so find an unused group number.
        group = self.modem.db.next_group()
        if group is not None:
            seq.add(self.db_add_resp_of, 0x01, self.modem.addr, group,
                    refresh=False)
        else:
            LOG.error("Can't create IOLinc simulated scene - there are no "
                      "unused modem scene numbers available")

        # Finally start the sequence running.  This will return so the
        # network event loop can process everything and the on_done callbacks
        # will chain everything together.
        seq.run()

    #-----------------------------------------------------------------------
    def set_flags(self, on_done, **kwargs):
        """Set internal device flags.

        This command is used to change internal device flags and states.  See
        the IOLinc user's guide for more information on what these do.  Valid
        inputs are:

        valid kwargs:
        - mode = "latching", "momentary-a", "momentary-b", "momentary-c":
          Change the relay mode.

        - trigger_reverse = 1/0:  Set the trigger reversing flag.

        - relay_linked = 1/0:  Set the relay link flag.

        Args:
          kwargs: Key=value pairs of the flags to change.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("IOLinc %s cmd: set operation flags", self.label)

        # Check the input flags to make sure only ones we can understand were
        # passed in.
        flags = set(["mode", "trigger_reverse", "relay_linked"])
        unknown = set(kwargs.keys()).difference(flags)
        if unknown:
            raise Exception("Unknown IOLinc flags input: %s.\n Valid flags "
                            "are: %s" % unknown, flags)

        # We need the existing bit set before we change it.  So to insure
        # that we are starting from the correct values, get the current bits
        # and pass that to the callback which will update them to make the
        # changes.
        callback = functools.partial(self._change_flags, kwargs=kwargs,
                                     on_done=util.make_callback(on_done))
        self.get_flags(on_done=callback)

        # FUTURE:momentary_time: extended set command: cmd: 0x2e 0x00
        #    D3 = 0x06
        #    D4 = momentary time in 0.10 sec: 0x02 -> 0xff
        # FUTURE: led backlight

    #-----------------------------------------------------------------------
    def _change_flags(self, success, msg, bits, kwargs, on_done):
        """Change the operating flags.

        See the set_flags() code for details.
        """
        if not success:
            on_done(success, msg, None)
            return

        # Mode might be None in which case it wasn't input.
        choices = ["latching", "momentary-a", "momentary-b", "momentary-c"]
        mode = util.input_choice(kwargs, "mode", choices)

        if mode == "latching":
            bits = util.bit_set(bits, 3, 0)
            bits = util.bit_set(bits, 4, 0)
            bits = util.bit_set(bits, 7, 0)
        elif mode == "momentary-a":
            bits = util.bit_set(bits, 3, 1)
            bits = util.bit_set(bits, 4, 0)
            bits = util.bit_set(bits, 7, 0)
        elif mode == "momentary-b":
            bits = util.bit_set(bits, 3, 1)
            bits = util.bit_set(bits, 4, 1)
            bits = util.bit_set(bits, 7, 0)
        elif mode == "momentary-c":
            bits = util.bit_set(bits, 3, 1)
            bits = util.bit_set(bits, 4, 1)
            bits = util.bit_set(bits, 7, 1)

        trigger_reverse = util.input_bool(kwargs, "trigger_reverse")
        if trigger_reverse is not None:
            bits = util.bit_set(bits, 6, trigger_reverse)

        relay_linked = util.input_bool(kwargs, "relay_linked")
        if relay_linked is not None:
            bits = util.bit_set(bits, 2, trigger_reverse)

        # This sends a refresh ping which will respond w/ the current
        # database delta field.  The handler checks that against the current
        # value.  If it's different, it will send a database download command
        # to the device to update the database.
        msg = Msg.OutStandard.direct(self.addr, 0x20, bits)
        msg_handler = handler.StandardCmd(msg, self.handle_flags)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def refresh(self, force=False, on_done=None):
        """Refresh the current device state and database if needed.

        This sends a ping to the device.  The reply has the current device
        state (on/off, level, etc) and the current db delta value which is
        checked against the current db value.  If the current db is out of
        date, it will trigger a download of the database.

        This will send out an updated signal for the current device status
        whenever possible (like dimmer levels).

        Args:
          force (bool):  If true, will force a refresh of the device database
                even if the delta value matches as well as a re-query of the
                device model information even if it is already known.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Device %s cmd: status refresh", self.label)

        # NOTE: IOLinc cmd1=0x00 will report the relay state.  cmd2=0x01
        # reports the sensor state which is what we want.
        seq = CommandSeq(self.protocol, "Device refreshed", on_done)

        # This sends a refresh ping which will respond w/ the current
        # database delta field.  The handler checks that against the current
        # value.  If it's different, it will send a database download command
        # to the device to update the database.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x01)
        msg_handler = handler.DeviceRefresh(self, self.handle_refresh, force,
                                            on_done, num_retry=3)
        seq.add_msg(msg, msg_handler)

        # If model number is not known, or force true, run get_model
        self.addRefreshData(seq, force)

        # Run all the commands.
        seq.run()

    #-----------------------------------------------------------------------
    def is_on(self):
        """Return if the device is on or not.
        """
        return self._is_on

    #-----------------------------------------------------------------------
    def on(self, group=0x01, level=None, instant=False, on_done=None):
        """Turn the relay on.

        This turns the relay on no matter what.  It ignores the momentary
        A/B/C settings and just turns the relay on.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group (int):  The group to send the command to.  For this device,
                this must be 1.  Allowing a group here gives us a consistent
                API to the on command across devices.
          level (int):  If non zero, turn the device on.  Should be in the
                range 0 to 255.  Only dimmers use the intermediate values, all
                other devices look at level=0 or level>0.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("IOLinc %s cmd: on", self.addr)
        assert group == 0x01

        # Send an on command.  Use the standard command handler which will
        # notify us when the command is ACK'ed.
        msg = Msg.OutStandard.direct(self.addr, 0x11, 0xff)
        msg_handler = handler.StandardCmd(msg, self.handle_ack, on_done)

        # Send the message to the PLM modem.
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def off(self, group=0x01, instant=False, on_done=None):
        """Turn the relay off.

        This turns the relay on no matter what.  It ignores the momentary
        A/B/C settings and just turns the relay on.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group (int):  The group to send the command to.  For this device,
                this must be 1.  Allowing a group here gives us a consistent
                API to the on command across devices.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("IOLinc %s cmd: off", self.addr)
        assert group == 0x01

        # Send an off command.  Use the standard command handler which will
        # notify us when the command is ACK'ed.
        msg = Msg.OutStandard.direct(self.addr, 0x13, 0x00)
        msg_handler = handler.StandardCmd(msg, self.handle_ack, on_done)

        # Send the message to the PLM modem.
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set(self, level, group=0x01, instant=False, on_done=None):
        """Turn the relay on or off.  Level zero will be off.

        This turns the relay on or off no matter what.  It ignores the
        momentary A/B/C settings and just turns the relay on.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.

        This will send the command to the device to update it's state.
        When we get an ACK of the result, we'll change our internal
        state and emit the state changed signals.

        Args:
          level (int):  If non zero, turn the device on.  Should be in the
                range 0 to 255.  Only dimmers use the intermediate values, all
                other devices look at level=0 or level>0.
          group (int):  The group to send the command to.  For this device,
                this must be 1.  Allowing a group here gives us a consistent
                API to the on command across devices.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        if level:
            self.on(group, level, instant, on_done)
        else:
            self.off(group, instant, on_done)

    #-----------------------------------------------------------------------
    def scene(self, is_on, group=None, on_done=None):
        """Trigger a scene on the device.

        Triggering a scene is the same as simulating a button press on the
        device.  It will change the state of the device and notify responders
        that are linked ot the device to be updated.

        Args:
          is_on (bool):  True for an on command, False for an off command.
          group (int):  The group on the device to simulate.  For this device,
                this must be 1.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        on_done = util.make_callback(on_done)

        # If we haven't found the virtual PLM scene yet, search for it now.
        if self.modem_scene is None:
            LOG.info("IOLinc %s finding correct modem scene to use",
                     self.label)

            entries = self.db.find_all(self.modem.addr, is_controller=False)
            for e in entries:
                if e.group != 0x01:
                    self.modem_scene = e.group
                    LOG.info("IOLinc %s found scene %s", self.label, e.group)
                    break
            else:
                LOG.error("Can't trigger IOLinc scene - there is no responder "
                          "from the modem in the IOLinc db")
                on_done(False, "Failed to send scene command", None)
                return

        # Tell the modem to send it's virtual scene broadcast to the IOLinc
        # device.
        LOG.info("IOLinc %s triggering modem scene %s", self.label,
                 self.modem_scene)
        self.modem.scene(is_on, self.modem_scene, on_done=on_done)

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        """Handle broadcast messages from this device.

        The broadcast message from a device is sent when the device is
        triggered.  The message has the group ID in it.  We'll update the
        device state and look up the group in the all link database.  For
        each device that is in the group (as a reponsder), we'll call
        handle_group_cmd() on that device to trigger it.  This way all the
        devices in the group are updated to the correct values when we see
        the broadcast message.

        Args:
          msg (InpStandard):  Broadcast message from the device.
        """
        # ACK of the broadcast - ignore this.
        if msg.cmd1 == 0x06:
            LOG.info("IOLinc %s broadcast ACK grp: %s", self.addr, msg.group)
            return

        # On command.  0x11: on
        elif msg.cmd1 == 0x11:
            LOG.info("IOLinc %s broadcast ON grp: %s", self.addr, msg.group)
            self._set_is_on(True)

        # Off command. 0x13: off
        elif msg.cmd1 == 0x13:
            LOG.info("IOLinc %s broadcast OFF grp: %s", self.addr, msg.group)
            self._set_is_on(False)

        # This will find all the devices we're the controller of for
        # this group and call their handle_group_cmd() methods to
        # update their states since they will have seen the group
        # broadcast and updated (without sending anything out).
        super().handle_broadcast(msg)

    #-----------------------------------------------------------------------
    def handle_flags(self, msg, on_done):
        """Callback for handling flag change responses.

        This is called when we get a response to the set_flags command.

        Args:
          msg (message.InpStandard):  The refresh message reply.  The current
              device state is in the msg.cmd2 field.
        """
        LOG.ui("Device %s operating flags: %s", self.addr,
               "{:08b}".format(msg.cmd2))

        # Setting latch/A/B/C by hand yields:
        #   76543210  bit numbers
        #   00000010  latching
        #   00001010  MOM A
        #   00011010  MOM B
        #   10011010  MOM C

        # From right to left (bit 0->7).  Values 1/0
        # B0 = program lock 1=on, 0=off
        # B1 = transmit LED 1=on, 0=off
        # B2 = relay linked 1=on, 0=off
        #        if 1, sensor on = relay on
        #              sensor off = relay off
        # B3 = latching 1=off, 1=on
        # B4 = B3=0 & B4=1: momentary B
        # B5 = X10 reversed 1=on, 0=off
        # B6 = trigger reverse 1=on, 0=off
        #        if 1, closed sensor = off
        #        if 0, closed sensor = on
        # B7 = B3=0 & B7=1: momentary C
        # If B3=0, B4=0, B7=0: momentary A
        bits = msg.cmd2
        LOG.ui("Program lock   : %d", util.bit_get(bits, 0))
        LOG.ui("Transmit LED   : %d", util.bit_get(bits, 1))
        LOG.ui("Relay linked   : %d", util.bit_get(bits, 2))
        LOG.ui("Trigger reverse: %d", util.bit_get(bits, 6))
        if not util.bit_get(bits, 3):
            mode = "latching"
        elif util.bit_get(bits, 7):
            mode = "momentary C"
        elif util.bit_get(bits, 4):
            mode = "momentary B"
        else:
            mode = "momentary A"

        # In the future, we should store this information and do something
        # with it.
        LOG.ui("Relay latching : %s", mode)
        on_done(True, "Operation complete", msg.cmd2)

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        """Callback for handling refresh() responses.

        This is called when we get a response to the refresh() command.  The
        refresh command reply will contain the current device state in cmd2
        and this updates the device with that value.  It is called by
        handler.DeviceRefresh when we can an ACK for the refresh command.

        Args:
          msg (message.InpStandard):  The refresh message reply.  The current
              device state is in the msg.cmd2 field.
        """
        LOG.ui("IOLinc %s refresh on=%s", self.label, msg.cmd2 > 0x00)

        # Current on/off level is stored in cmd2 so update our level to
        # match.
        self._set_is_on(msg.cmd2 > 0x00)

    #-----------------------------------------------------------------------
    def handle_ack(self, msg, on_done):
        """Callback for standard commanded messages.

        This callback is run when we get a reply back from one of our
        commands to the device.  If the command was ACK'ed, we know it worked
        so we'll update the internal state of the device and emit the signals
        to notify others of the state change.

        Args:
          msg (message.InpStandard):  The reply message from the device.
              The on/off level will be in the cmd2 field.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # Note: don't update the state - the sensor does that.  This state is
        # for the relay.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("IOLinc %s ACK: %s", self.addr, msg)
            on_done(True, "IOLinc command complete", None)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("IOLinc %s NAK error: %s, Message: %s", self.addr,
                      msg.nak_str(), msg)
            on_done(False, "IOLinc command failed. " + msg.nak_str(), None)

    #-----------------------------------------------------------------------
    def handle_scene(self, msg, on_done):
        """Callback for scene simulation commanded messages.

        This callback is run when we get a reply back from triggering a scene
        on the device.  If the command was ACK'ed, we know it worked.  The
        device will then send out standard broadcast messages which will
        trigger other updates for the scene devices.

        Args:
          msg (message.InpStandard): The reply message from the device.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # Call the callback.  We don't change state here - the device will
        # send a regular broadcast message which will run handle_broadcast
        # which will then update the state.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("IOLinc %s ACK: %s", self.addr, msg)
            on_done(True, "Scene triggered", None)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("IOLinc %s NAK error: %s, Message: %s", self.addr,
                      msg.nak_str(), msg)
            on_done(False, "Scene trigger failed failed. " + msg.nak_str(),
                    None)

    #-----------------------------------------------------------------------
    def handle_group_cmd(self, addr, msg):
        """Respond to a group command for this device.

        This is called when this device is a responder to a scene.  The
        device that received the broadcast message (handle_broadcast) will
        call this method for every device that is linked to it.  The device
        should look up the responder entry for the group in it's all link
        database and update it's state accordingly.

        Args:
          addr (Address):  The device that sent the message.  This is the
               controller in the scene.
          msg (InpStandard):  Broadcast message from the device.  Use
              msg.group to find the group and msg.cmd1 for the command.
        """
        # Make sure we're really a responder to this message.  This shouldn't
        # ever occur.
        entry = self.db.find(addr, msg.group, is_controller=False)
        if not entry:
            LOG.error("IOLinc %s has no group %s entry from %s", self.addr,
                      msg.group, addr)
            return

        # Nothing to do - there is no "state" to update since the state we
        # care about is the sensor state and this command tells us that the
        # relay state was tripped.
        LOG.debug("IOLinc %s cmd %#04x", self.addr, msg.cmd1)

    #-----------------------------------------------------------------------
    def _set_is_on(self, is_on):
        """Update the device on/off state.

        This will change the internal state and emit the state changed
        signals.  It is called by whenever we're informed that the device has
        changed state.

        Args:
          is_on (bool):  True if the relay is on, False if it isn't.
        """
        LOG.info("Setting device %s on %s", self.label, is_on)
        self._is_on = bool(is_on)

        self.signal_on_off.emit(self, self._is_on)

    #-----------------------------------------------------------------------
