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

    A motion sensor is an on/off sensor except that it's battery powered and
    only awake when motion is detected or the set button is pressed.

    The issue with a battery powered sensors is that we can't download the
    link database without the sensor being on.  You can trigger the sensor
    manually and then quickly send an MQTT command with the payload 'getdb'
    to download the database.  We also can't test to see if the local
    database is current or what the current motion state is - we can really
    only respond to the sensor when it sends out a message.

    Motion sensors send a Motion.signal_on_off signal (from BatterySensor)
    when motion is detected.  Some motion sensors also support a dusk/dawn
    light sensor.  In that case, the Motion.signal_dawn signal is emitted
    when the light sensor changes state.

    The motion sensor supports the following input commands (note these only
    work if the sensor is awake): devices are:

       getdb:  No arguments.  Download the PLM modem all link database
               and save it to file.
       refresh:  No arguments.  Ping the device and see if the database is
                 current.  Reloads the modem database if needed.
    """
    def __init__(self, protocol, modem, address, name=None):
        """Constructor

        Args:
          protocol (Protocol):  The Protocol object used to communicate
                   with the Insteon network.  This is needed to allow the
                   device to send messages to the PLM modem.
          modem (Modem):  The Insteon modem used to find other devices.
          address (Address): The address of the device.
          name (str):  Nice alias name to use for the device.
        """
        super().__init__(protocol, modem, address, name)

        self.signal_dawn = Signal()  # (Device, bool is_dawn)

        # Insert the dawn/dusk callback on group 02.  Base class already
        # handles the other groups.
        self.group_map[0x02] = self.handle_dawn

    #-----------------------------------------------------------------------
    def handle_dawn(self, msg):
        """Handle a dusk/dawn message.

        This is called by the BatterySensor base class when a group broadcast
        on group 02 is sent out by the sensor.

        Args:
          msg:   (InpStandard) Broadcast message from the device.
        """
        # Send True for dawn, False for dusk.
        self.signal_dawn.emit(msg.cmd1 == 0x11)

    #-----------------------------------------------------------------------
