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

        # This sends a refresh ping which will respond w/ the LED bit
        # flags (1-8) and current database delta field.  The handler
        # checks that against the current value.  If it's different,
        # it will send a database download command to the device to
        # update the database.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x01)
        msg_handler = handler.DeviceRefresh(self, self.handle_led_refresh,
                                            force=False, on_done=None,
                                            num_retry=3)
        self.protocol.send(msg, msg_handler)

        # Get the light level state.
        super().refresh(force, on_done=on_done)

    #-----------------------------------------------------------------------
    def set_button_led(self, button, on, on_done=None):
        """TODO: doc
        """
        LOG.info("KeypadLinc setting LED %s to %s", button, on)

        if button < 1 or button > 8:
            LOG.error("KeypadLinc button %s out of range [1,8]", button)
            return

        is_on = self._led_bits & (1 << (button - 1))
        if is_on == on:
            LOG.info("KeypadLinc LED %s already at %s", button, on)
            return

        # Extended message data - see Insteon dev guide p156.
        data = bytes([
            button,  # D1 button number
            0x09,    # D2 set LED state for button
            0x01 if on else 0x00,  # D3 turn on/off button
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when
        # the command is ACK'ed.
        callback = functools.partial(self.handle_led_ack, on=on,
                                     on_done=on_done)
        msg_handler = handler.StandardCmd(msg, callback)

        # Send the message to the PLM modem for protocol.
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_led_ack(self, msg, on, on_done=None):
        """TODO: doc
        """
        # If this it the ACK we're expecting, update the internal
        # state and emit our signals.
        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            LOG.debug("KeypadLinc LED %s ACK: %s", self.addr, msg)

            assert 1 <= msg.group <= 8

            # Update the LED bit for the button.
            self._led_bits |= (1 << (msg.group - 1))

            # Emit the LED change signal
            self.signal_led_changed.emit(self, msg.group, on)

            if on_done:
                s = "KeypadLinc %s LED updated to %s" % (self.addr, on)
                on_done(True, s, on)

        elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            LOG.error("KeypadLinc LED %s NAK error: %s", self.addr, msg)
            if on_done:
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
            mask = 1 << i
            is_on = led_bits & mask
            was_on = self._led_bits & mask
            if is_on != was_on:
                self.signal_led_changed.emit(self, i + 1, is_on)

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

        on = None
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
            on = True

        # Off command. 0x13: off, 0x14: off fast
        elif cmd in self.off_codes:
            LOG.info("KeypadLinc %s broadcast OFF grp: %s", self.addr,
                     msg.group)

        # Starting manual increment (cmd2 0x00=up, 0x01=down)
        elif cmd == 0x17:
            # This is kind of arbitrary - but if the button is held
            # down we'll emit an on signal if it's dimming up and an
            # off signal if it's dimming down.
            on = msg.cmd2 == 0x00  # on = up, off = down

        # Stopping manual increment (cmd2 = unused)
        elif cmd == 0x18:
            # Nothing to do - the remote has no state to query about.
            pass

        # Notify others that the button was pressed.
        if on is not None:
            self.signal_pressed.emit(self, msg.group, True)

        # This will find all the devices we're the controller of for
        # this group and call their handle_group_cmd() methods to
        # update their states since they will have seen the group
        # broadcast and updated (without sending anything out).
        super().handle_broadcast(msg)

    #-----------------------------------------------------------------------
