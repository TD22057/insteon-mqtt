#===========================================================================
#
# Insteon battery powered motion sensor
#
#===========================================================================
from .BatterySensor import BatterySensor
from .. import log
from ..Signal import Signal

LOG = log.get_logger()


class Motion(BatterySensor):
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

    TODO: groups 1, 2, 3 discussion and other signals

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

        self.signal_dawn = Signal()  # (Device, bool)

        # Dawn/dusk is on group 02.
        self.group_map[0x02] = self.handle_dawn

    #-----------------------------------------------------------------------
    def handle_dawn(self, msg):
        """TODO: doc
        """
        # Send True for dawn, False for dusk.
        self.signal_dawn.emit(msg.cmd1 == 0x11)

    #-----------------------------------------------------------------------
