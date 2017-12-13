#===========================================================================
#
# KeypadLinc module
#
#===========================================================================
from .. import log
from ..Signal import Signal
from .Base import Base
from .Dimmer import Dimmer

LOG = log.get_logger()


class KeypadLinc(Dimmer):
    """Insteon KeypadLinc dimmer plus remote module

    TODO: docs
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

        self.signal_pressed = Signal()  # (Device, int group, bool on)

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
            LOG.info("KeypadLinc %s broadcast ACK grp: %s", self.addr,
                     msg.group)
            return

        # On command.  0x11: on, 0x12: on fast
        elif msg.cmd1 in self.on_codes:
            LOG.info("KeypadLinc %s broadcast ON grp: %s", self.addr,
                     msg.group)
            on = True

        # Off command. 0x13: off, 0x14: off fast
        elif msg.cmd1 in self.off_codes:
            LOG.info("KeypadLinc %s broadcast OFF grp: %s", self.addr,
                     msg.group)
            on = False

        # Notify others that the button was pressed.
        self.signal_pressed.emit(self, msg.group, on)

        # For the dimmer, we only want to have the dimmer process the
        # message if it's group 1.  This also calls Base.handle_broadcast.
        if msg.group == 1:
            Dimmer.handle_broadcast(self, msg)

        # Other call the device base handler.  This will find all the
        # devices we're the controller of for this group and call
        # their handle_group_cmd() methods to update their states
        # since they will have seen the group broadcast and updated
        # (without sending anything out).
        else:
            Base.handle_broadcast(self, msg)

    #-----------------------------------------------------------------------
