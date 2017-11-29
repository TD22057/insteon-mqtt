#===========================================================================
#
# Dimmer module
#
#===========================================================================
import logging
from .Base import Base

LOG = logging.getLogger(__name__)


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

    def __init__(self, protocol, modem, address, num, name=None):
        """Constructor

        Args:
          protocol:    (Protocol) The Protocol object used to communicate
                       with the Insteon network.  This is needed to allow
                       the device to send messages to the PLM modem.
          modem:       (Modem) The Insteon modem used to find other devices.
          address:     (Address) The address of the device.
          num:         (int) Number of buttons on the remote.
          name         (str) Nice alias name to use for the device.
        """
        super().__init__(protocol, modem, address, name)
        self.num = num

    #-----------------------------------------------------------------------
    def pair(self):
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

        # Search our db to see if we have controller links for the
        # groups back to the modem.  If one doesn't exist, add it on
        # our device and the modem.
        for group in range(1, self.num + 1):
            if not self.db.find(self.modem.addr, group, True):
                LOG.info("Remote adding ctrl for group %s", group)
                self.db_add_ctrl_of(self.modem.addr, group)

    #-----------------------------------------------------------------------
    def refresh(self):
        """Refresh the current device state and database if needed.

        This sends a ping to the device.  The reply has the current
        device state (on/off, level, etc) and the current db delta
        value which is checked against the current db value.  If the
        current db is out of date, it will trigger a download of the
        database.

        This will send out an updated signal for the current device
        status whenever possible (like dimmer levels).
        """
        # TODO: figure out if we can ping the remote and get any kind
        # of state from it including the database version.
        pass

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
            LOG.info("Remote %s broadcast ACK grp: %s", self.addr, msg.group)
            return

        # On command.  0x11: on, 0x12: on fast
        elif msg.cmd1 in Remote.on_codes:
            LOG.info("Remote %s broadcast ON grp: %s", self.addr, msg.group)

        # Off command. 0x13: off, 0x14: off fast
        elif msg.cmd1 in Remote.off_codes:
            LOG.info("Remote %s broadcast OFF grp: %s", self.addr, msg.group)

        # TODO: test this w/ remote buttons to see what the groups are.

        # This will find all the devices we're the controller of for
        # this group and call their handle_group_cmd() methods to
        # update their states since they will have seen the group
        # broadcast and updated (without sending anything out).
        super().handle_broadcast(msg)

        # TODO: once Motion is working - apply that here.

    #-----------------------------------------------------------------------
