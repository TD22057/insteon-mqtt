#===========================================================================
#
# Remote module
#
#===========================================================================
from ..CommandSeq import CommandSeq
from .. import log
from ..Signal import Signal
from .Base import Base

LOG = log.get_logger()


class Remote(Base):
    """Insteon multi-button mini-remote device.

    TODO: docs

    Sample configuration input:

        insteon:
          devices:
            - mini_remote4:
              name: "Remote A"
              address: 44.a3.79

            - mini_remote8:
              name: "Remote B"
              address: 44.a3.80

    The issue with a battery powered remotes is that we can't download
    the link database without the remote being on.  You can trigger
    the remote manually and then quickly send an MQTT command with the
    payload 'getdb' to download the database.  We also can't test to
    see if the local database is current or what the current motion
    state is - we can really only respond to the remote when it sends
    out a message.

    The Signal Switch.signal_active will be emitted whenever
    the device button is pushed.

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
    """

    on_codes = [0x11, 0x12, 0x21, 0x23]  # on, fast on, instant on, manual on
    off_codes = [0x13, 0x14, 0x22]  # off, fast off, instant off

    def __init__(self, protocol, modem, address, name, num_button):
        """Constructor

        Args:
          protocol:    (Protocol) The Protocol object used to communicate
                       with the Insteon network.  This is needed to allow
                       the device to send messages to the PLM modem.
          modem:       (Modem) The Insteon modem used to find other devices.
          address:     (Address) The address of the device.
          name         (str) Nice alias name to use for the device.
          num_button:  (int) Number of buttons on the remote.
        """
        super().__init__(protocol, modem, address, name)
        self.num = num_button

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
        LOG.info("Remote %s pairing", self.addr)

        # Build a sequence of calls to the do the pairing.  This insures each
        # call finishes and works before calling the next one.  We have to do
        # this for device db manipulation because we need to know the memory
        # layout on the device before making changes.
        seq = CommandSeq(self.protocol, "Remote paired", on_done)

        # Start with a refresh command - since we're changing the db, it must
        # be up to date or bad things will happen.
        seq.add(self.refresh)

        # Add the device as a responder to the modem on group 1.  This is
        # probably already there - and maybe needs to be there before we can
        # even issue any commands but this check insures that the link is
        # present on the device and the modem.
        seq.add(self.db_add_resp_of, self.modem.addr, 0x01, refresh=False)

        # Now add the device as the controller of the modem for all the
        # remote buttons.
        for group in range(1, self.num + 1):
            seq.add(self.db_add_ctrl_of, self.modem.addr, group, refresh=False)

        # Finally start the sequence running.  This will return so the
        # network event loop can process everything and the on_done callbacks
        # will chain everything together.
        seq.run()

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
        is_on = None
        cmd = msg.cmd1

        # ACK of the broadcast - ignore this.
        if cmd == 0x06:
            LOG.info("Remote %s broadcast ACK grp: %s", self.addr, msg.group)
            return

        # On command.  0x11: on, 0x12: on fast
        elif cmd in Remote.on_codes:
            LOG.info("Remote %s broadcast ON grp: %s", self.addr, msg.group)
            is_on = True

        # Off command. 0x13: off, 0x14: off fast
        elif cmd in Remote.off_codes:
            LOG.info("Remote %s broadcast OFF grp: %s", self.addr, msg.group)
            is_on = False

        # Starting manual increment (cmd2 0x00=up, 0x01=down)
        elif cmd == 0x17:
            # This is kind of arbitrary - but if the button is held
            # down we'll emit an on signal if it's dimming up and an
            # off signal if it's dimming down.
            is_on = msg.cmd2 == 0x00  # on = up, off = down

        # Stopping manual increment (cmd2 = unused)
        elif cmd == 0x18:
            # Nothing to do - the remote has no state to query about.
            pass

        # Notify others that the button was pressed.
        if is_on is not None:
            self.signal_pressed.emit(self, msg.group, is_on)

        # This will find all the devices we're the controller of for
        # this group and call their handle_group_cmd() methods to
        # update their states since they will have seen the group
        # broadcast and updated (without sending anything out).
        super().handle_broadcast(msg)

        # Since we just saw a message got by, yse this opportunity to
        # get the device db since we know the sensor is awake.  This
        # doesn't always work - but it works enough times to be useful
        # (probably?).
        if len(self.db) == 0:
            LOG.info("Remote %s awake - requesting database", self.addr)
            self.refresh(force=True)

    #-----------------------------------------------------------------------
