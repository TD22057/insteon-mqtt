#===========================================================================
#
# KeypadLinc module
#
#===========================================================================
import functools
from .. import handler
from .. import log
from .. import message as Msg
from ..Signal import Signal
from .. import util
from .Dimmer import Dimmer

LOG = log.get_logger()


class KeypadLinc(Dimmer):
    """Insteon KeypadLinc dimmer plus remote module

    TODO: docs


    Each button (up to 8) has an LED light.  Light status can be
    retrieved by sending 0x19 0x01 which returns cmd1=db delta and
    cmd2=LED bit flags.

    # TODO: to set LED brightess: D1=0x00 D2 = 0x07 D3 = 0x11->0x7f
    # TODO: to trigger all link state: D2 = 0x0C
    """
    def __init__(self, protocol, modem, address, name):
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

        # 8 bits representing the LED's on the device.
        self._led_bits = 0x00

        self.signal_pressed = Signal()  # (Device, int group, bool on)
        self.signal_led_changed = Signal()  # (Device, int group, bool on)

        # Remote (mqtt) commands mapped to methods calls.  Add to the
        # base class defined commands.
        self.cmd_map.update({
            'set_button_led' : self.set_button_led,
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

        NOTE: The remote code assumes the remote buttons are using
        groups 1...num (as set in the constructor).
        """
        LOG.info("KeypadLinc %s pairing", self.addr)

        # Search our db to see if we have controller links for the
        # groups back to the modem.  If one doesn't exist, add it on
        # our device and the modem.
        add_groups = []
        for group in range(1, 8):
            if not self.db.find(self.modem.addr, group, True):
                LOG.info("KeypadLinc adding ctrl for group %s", group)
                add_groups.append(group)
            else:
                LOG.ui("KeypadLinc ctrl for group %s already exists", group)

        if add_groups:
            for group in add_groups:
                callback = on_done if group == add_groups[-1] else None
                self.db_add_ctrl_of(self.modem.addr, group, on_done=callback)
        elif on_done:
            on_done(True, "Pairings already exist", None)

    #-----------------------------------------------------------------------
    def refresh(self, force=False, on_done=None):
        """TODO doc
        """
        # Send a 0x19 0x01 command to get the LED light on/off flags.
        LOG.info("Device %s cmd: keypad status refresh", self.addr)

        # Get the dimmer light level state if the initial refresh works.
        def use_cb(success, msg, data):
            if success:
                Dimmer.refresh(self, force, on_done)
            elif on_done:
                on_done(False, "Refresh failed", None)

        # This sends a refresh ping which will respond w/ the LED bit
        # flags (1-8) and current database delta field.  The handler
        # checks that against the current value.  If it's different,
        # it will send a database download command to the device to
        # update the database.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x01)
        msg_handler = handler.DeviceRefresh(self, self.handle_led_refresh,
                                            force=False, on_done=use_cb,
                                            num_retry=3)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_button_led(self, button, is_on, on_done=None):
        """TODO: doc
        """
        on_done = util.make_callback(on_done)
        LOG.info("KeypadLinc setting LED %s to %s", button, is_on)

        if button < 1 or button > 8:
            LOG.error("KeypadLinc button %s out of range [1,8]", button)
            on_done(False, "Invalid button", None)
            return

        # New LED bit flags to send.  Either set the bit or clear it
        # depending on the input flag.
        util.bit_set(self._led_bits, button - 1, is_on)

        # Extended message data - see Insteon dev guide p156.  NOTE: guide is
        # wrong - it says send button, 0x09, 0x01/0x00 to turn that button
        # on/off but that doesn't work.  Must send button 0x01 and the full
        # LED bit mask to adjust the lights.
        data = bytes([
            0x01,   # D1 only button 0x01 works
            0x09,   # D2 set LED state for buttons
            led_bits,  # D3 all 8 LED flags.
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when
        # the command is ACK'ed.
        callback = functools.partial(self.handle_led_ack, button=button,
                                     is_on=is_on, led_bits=led_bits,
                                     on_done=on_done)
        msg_handler = handler.StandardCmd(msg, callback)

        # Send the message to the PLM modem for protocol.
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_led_ack(self, msg, button, is_on, led_bits, on_done=None):
        """TODO: doc
        """
        # If this it the ACK we're expecting, update the internal
        # state and emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc LED %s button %s ACK: %s", self.addr, button,
                      msg)

            # Update the LED bit for the updated button.
            self._led_bits = led_bits
            LOG.ui("KeypadLinc %s LED's changed to %s", self.addr,
                   "{:08b}".format(self._led_bits))

            # Emit the LED change signal
            self.signal_led_changed.emit(self, button, is_on)

            msg = "KeypadLinc %s LED updated to %s" % (self.addr, is_on)
            on_done(True, msg, is_on)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc LED %s NAK error: %s", self.addr, msg)
            on_done(False, "KeypadLinc %s LED update failed", None)

    #-----------------------------------------------------------------------
    def handle_led_refresh(self, msg):
        """TODO: doc
        """
        led_bits = msg.cmd2

        # Current the led speed is stored in cmd2 so update our speed to
        # match.
        LOG.ui("KeypadLinc %s setting LED bits %s", self.addr,
               "{:08b}".format(led_bits))

        # Loop over the bits and emit a signal for any that have been
        # changed.
        for i in range(8):
            is_on = util.bit_get(led_bits, i)
            was_on = util.bit_get(self._led_bits, i)

            LOG.debug("Btn %d old: %d new %d", i + 1, is_on, was_on)
            if is_on != was_on:
                self.signal_led_changed.emit(self, i + 1, is_on)
                self.signal_pressed.emit(self, i + 1, is_on)

        self._led_bits = led_bits

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
        # For the dimmer, we only want to have the dimmer process the
        # message if it's group 1.  This also calls
        # Base.handle_broadcast.  This correctly handles the dimmer
        # and load settings.
        if msg.group == 1:
            Dimmer.handle_broadcast(self, msg)
            return

        # Non-group 1 messages are for the scene buttons on
        # keypadlinc.  Treat those the same as the remote control
        # does.  They don't have levels to find/set but have similar
        # messages to the dimmer load.
        is_on = None
        cmd = msg.cmd1

        # ACK of the broadcast - ignore this.
        if cmd == 0x06:
            LOG.info("KeypadLinc %s broadcast ACK grp: %s", self.addr,
                     msg.group)
            return

        # On command.  0x11: on, 0x12: on fast
        elif cmd in self.on_codes:
            LOG.info("KeypadLinc %s broadcast ON grp: %s", self.addr,
                     msg.group)
            is_on = True

        # Off command. 0x13: off, 0x14: off fast
        elif cmd in self.off_codes:
            LOG.info("KeypadLinc %s broadcast OFF grp: %s", self.addr,
                     msg.group)
            is_on = False

        # Starting manual increment (cmd2 0x00=up, 0x01=down)
        elif cmd == 0x17:
            LOG.info("KeypadLinc %s starting manual change grp: %s %s",
                     self.addr, msg.group, "UP" if msg.cmd2 == 0x00 else "DN")

        # Stopping manual increment (cmd2 = unused)
        elif cmd == 0x18:
            LOG.info("KeypadLinc %s stopping manual change grp %s", self.addr,
                     msg.group)

            # Ping the device to get the button states - we don't know what
            # the keypadlinc things the state is - could be on or off.  Doing
            # a dim down for a long time puts all the other devices "off" but
            # the keypadlinc can still think that it's on.  So we have to do
            # a refresh to find out.
            self.refresh()

        # Notify others that the button was pressed.
        if is_on is not None:
            self._led_bits = util.bit_set(self._led_bits, msg.group - 1, is_on)
            self.signal_pressed.emit(self, msg.group, is_on)

        # This will find all the devices we're the controller of for
        # this group and call their handle_group_cmd() methods to
        # update their states since they will have seen the group
        # broadcast and updated (without sending anything out).
        super(Dimmer,self).handle_broadcast(msg)

    #-----------------------------------------------------------------------
