#===========================================================================
#
# Insteon battery powered motion sensor
#
#===========================================================================
import enum
from .BatterySensor import BatterySensor
from .. import log

LOG = log.get_logger()


class Leak(BatterySensor):
    """Insteon battery powered water leak sensor.

    A leak sensor is basically an on/off sensor except that it's
    batter powered and only awake when water is detected or the set
    button is pressed.  It will broadcast an on command for group 1
    when dry and on command for group 2 when wet.

    The issue with a battery powered sensor is that we can't download
    the link database without the sensor being on.  You can trigger
    the sensor manually and then quickly send an MQTT command with the
    payload 'getdb' to download the database.  We also can't test to
    see if the local database is current or what the current motion
    state is - we can really only respond to the sensor when it sends
    out a message.

    The Signal Leak.signal_active(True) will be emitted whenever the
    device senses water and signal_actdive(False) when no water is detected.

    TODO: download the database automatically when motion is seen.
    """
    # broadcast group ID alert description
    class Type(enum.IntEnum):
        WET = 0x02

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

        # Leak sensor uses group 1 for dry, group 2 for wet.
        self.group_map[0x01] = self.handle_dry
        self.group_map[0x02] = self.handle_wet

    #-----------------------------------------------------------------------
    def handle_dry(self, msg):
        """TODO: doc
        """
        # off = dry, on == wet
        self._set_is_on(False)

    #-----------------------------------------------------------------------
    def handle_wet(self, msg):
        """TODO: doc
        """
        # off = dry, on == wet
        self._set_is_on(True)

    #-----------------------------------------------------------------------
    def handle_heartbeat(self, msg):
        """TODO: doc
        """
        # Update the wet/dry state using the heartbeat if needed.
        is_wet = msg.cmd1 == 0x13
        if self._is_on != is_wet:
            self._set_is_on(is_wet)

        super().handle_heartbeat(msg)

    #-----------------------------------------------------------------------
