#===========================================================================
#
# Insteon leak sensor
#
#===========================================================================
from .BatterySensor import BatterySensor
from .. import log

LOG = log.get_logger()


class Leak(BatterySensor):
    """Insteon battery powered water leak sensor.

    A leak sensor is basically an on/off sensor except that it's batter
    powered and only awake when water is detected or the set button is
    pressed.  It will broadcast an on command for group 1 when dry and on
    command for group 2 when wet. It will also broadcast a heartbeat signal
    every 24 hours on group 4.

    The issue with a battery powered sensor is that we can't download the
    link database without the sensor being on.  You can trigger the sensor
    manually and then quickly send an MQTT command with the payload 'getdb'
    to download the database.  We also can't test to see if the local
    database is current or what the current motion state is - we can really
    only respond to the sensor when it sends out a message.

    The device will broadcast messages on the following groups:
      group 01 = dry condition
      group 02 = wet condition
      group 04 = heartbeat (0x11)

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).  Supported signals are:

    - signal_wet( Device, bool is_wet ): Sent when the sensor is tripped
      (is_wet=True) or cleraed (is_wet=False).

    - signal_heartbeat( Device, True ): Sent when the device has broadcast a
      heartbeat signal.
    """
    type_name = "leak_sensor"
    GROUP_DRY = 1
    GROUP_WET = 2

    def __init__(self, protocol, modem, address, name=None):
        """Constructor

        Args:
          protocol (Protocol):  The Protocol object used to communicate
                   with the Insteon network.  This is needed to allow the
                   device to send messages to the PLM modem.
          modem (Modem):  The Insteon modem used to find other devices.
          address (Address):  The address of the device.
          name (str):  Nice alias name to use for the device.
        """
        super().__init__(protocol, modem, address, name)

        # Maps Insteon groups to message type for this sensor.
        self.group_map = {
            # Dry event on group 1.
            0x01 : self.handle_on_off,
            # Wet event on group 2.
            0x02 : self.handle_on_off,
            # Heartbeat is on group 4
            0x04 : self.handle_heartbeat,
            }

        self._is_wet = False

    #-----------------------------------------------------------------------
    def _cache_state(self, group, is_on, level, reason):
        """Cache the State of the Device

        Used to help with the unique device functions.

        Args:
          group (int): The group which this applies
          is_on (bool): Whether the device is on.
          level (int): The new device level in the range [0,255].  0 is off.
          reason (str): Reason string to pass around.
        """
        # Handle_Refresh sends level and not is_on
        if is_on is None:
            if level is not None:
                is_on = level > 0
            else:
                return  # No on data?
        if not is_on:
            self._is_wet = False
        else:
            if group == self.GROUP_WET:
                self._is_wet = True
            elif group == self.GROUP_DRY:
                self._is_wet = False

    #-----------------------------------------------------------------------
    def handle_heartbeat(self, msg):
        """Handle a heartbeat message.

        This is called by the device when a group broadcast on group 04 is
        sent out by the sensor.  Not all devices send heartbeats.

        Leak sensors also include the wet/dry status in the heartbeat so
        we'll update that if it changes.

        Args:
          msg (InpStandard):  Broadcast message from the device.
        """
        LOG.info("LeakSensor %s received heartbeat", self.label)
        # Update the wet/dry state using the heartbeat if needed.
        is_wet = msg.cmd1 == 0x13
        if self._is_wet != is_wet:
            self._set_state(group=self.GROUP_WET, is_on=is_wet)

        # Send True for any heart beat message
        self.signal_heartbeat.emit(self, True)
        self.update_linked_devices(msg)

    #-----------------------------------------------------------------------
    def refresh(self, force=False, group=None, on_done=None):
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
        # Needed to pass the GROUP_WET data to base refresh()
        group = group if group is not None else self.GROUP_WET
        super().refresh(force=force, group=group, on_done=on_done)

    #-----------------------------------------------------------------------
