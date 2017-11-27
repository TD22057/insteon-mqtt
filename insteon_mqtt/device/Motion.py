#===========================================================================
#
# Insteon battery powered motion sensor
#
#===========================================================================
import logging
from .Base import Base
from ..Signal import Signal

LOG = logging.getLogger(__name__)


class Motion(Base):
    """Insteon battery powered motion sensor.

    A motion sensor is basically an on/off sensor except that it's
    batter powered and only awake when motion is detected or the set
    button is pressed.  It will broadcast on conditiions when motion
    is detected and off after some interval.

    The issue with a battery powered sensor is that we can't download
    the link database without the sensor being on.  You can trigger
    the sensor manually and then quickly send an MQTT command with the
    payload 'getdb' to download the database.  We also can't test to
    see if the local database is current or what the current motion
    state is - we can really only respond to the sensor when it sends
    out a message.

    The Signal Motion.signal_acdtive will be emitted whenever the
    device triggers motion on or off with the calling sequence
    (device, on) where on is True for motion and False for no motoin.

    TODO: download the database automatically when motion is seen.

    Sample configuration input:

        insteon:
          devices:
            - motion:
              name: "Upstairs Hallway"
              address: 44.a3.79

    The run_command() method is used for arbitrary remote commanding
    (via MQTT for example).  The input is a dict (or keyword args)
    containing a 'cmd' key with the value as the command name and any
    additional arguments needed for the command as other key/value
    pairs. Valid commands for all devices are:

       getdb:    No arguments.  Download the PLM modem all link database
                 and save it to file.
       refresh:  No arguments.  Ping the device and see if the database is
                 current.  Reloads the modem database if needed.
    """
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

        self.signal_active = Signal()  # (Device, bool)

        self._is_on = False

        # True if we've got a local db.  If this is false, we'll try
        # and download the db when the sensor is awake.
        self._have_db = False

    #-----------------------------------------------------------------------
    def pair(self):
        """Pair the device with the modem.

        This only needs to be called one time.  It will set the device
        as a controller and the modem as a responder for motion sensor
        alerts.

        The device must already be a responder to the modem (push set
        on the modem, then set on the device) so we can update it's
        database.
        """
        LOG.info("TODO: Motion %s pairing", self.addr)
        # TODO: check the modem db for the associations and call this if
        # they're not there.

    #-----------------------------------------------------------------------
    def is_on(self):
        """Return if motion has been sensed.
        """
        return self._is_on

    #-----------------------------------------------------------------------
    def load_db(self):
        """Load the all link database from a file.

        The file is stored in JSON format (by save_db()) and has the
        path self.db_path().  If the file doesn't exist, nothing is
        done.
        """
        super().load_db()
        self._have_db = len(self.db) > 0

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        """Handle broadcast messages from this device.

        The broadcast message from a device is sent when the device is
        triggered and when the motion expires.  The message has the
        group ID in it.  We'll update the device state and look up the
        group in the all link database.  For each device that is in
        the group (as a reponsder), we'll call handle_group_cmd() on
        that device to trigger it.  This way all the devices in the
        group are updated to the correct values when we see the
        broadcast message.

        Args:
          msg:   (InptStandard) Broadcast message from the device.
        """
        # ACK of the broadcast - ignore this.
        if msg.cmd1 == 0x06:
            LOG.info("Motion %s broadcast ACK grp: %s", self.addr, msg.group)
            return

        # On command.
        elif msg.cmd1 == 0x11:
            LOG.info("Motion %s broadcast ON grp: %s", self.addr, msg.group)
            self._set_is_on(True)

        # Off command.
        elif msg.cmd1 == 0x13:
            LOG.info("Motion %s broadcast OFF grp: %s", self.addr, msg.group)
            self._set_is_on(False)

        # Broadcast to the devices we're linked to. Call
        # handle_broadcast for any device that we're the controller of.
        LOG.debug("Motion %s have db %s", self.addr, len(self.db))
        super().handle_broadcast(msg)

        # Use this opportunity to get the device db since we know the
        # sensor is awake.
        if not self._have_db:
            # TODO: how to get db when sensor is awake.
            # This isn't working - maybe need to wait for all the
            # broadcast messages to arrive?
            pass
            #LOG.info("Motion %s awake - requesting database", self.addr)
            #self._saved_broadcast = msg
            #self.get_db(db_delta=0)
            #self.refresh()

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        """Handle replies to the refresh command.

        The refresh command reply will contain the current device
        state in cmd2 and this updates the device with that value.

        NOTE: refresh() will not work if the device is asleep.

        Args:
          msg:  (message.InpStandard) The refresh message reply.  The current
                device state is in the msg.cmd2 field.
        """
        LOG.debug("Motion %s refresh message: %s", self.addr, msg)

        # Current on/off level is stored in cmd2 so update our state
        # to match.
        self._set_is_on(msg.cmd2 != 0x00)

    #-----------------------------------------------------------------------
    def _set_is_on(self, is_on):
        """Set the device on/off state.

        This will change the internal state and emit the state changed
        signal.

        Args:
          is_on:   (bool) True if motion is active, False if it isn't.
        """
        LOG.info("Setting device %s '%s' on %s", self.addr, self.name, is_on)
        self._is_on = is_on
        self.signal_active.emit(self, self._is_on)

    #-----------------------------------------------------------------------
