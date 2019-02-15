#===========================================================================
#
# Insteon battery powered motion sensor
#
#===========================================================================
from .Base import Base
from ..CommandSeq import CommandSeq
from .. import log
from ..Signal import Signal

LOG = log.get_logger()


class BatterySensor(Base):
    """Insteon battery powered sensor.

    Battery powered sensors send basic on/off commands, low battery warnings,
    and hearbeat messages (some devices).  This includes things like door
    sensors, hidden door sensors, and window sensors.  This class also serves
    as the base class for other battery sensors like motion sensors.

    The issue with a battery powered sensor is that we can't download the
    link database without the sensor being on.  You can trigger the sensor
    manually and then quickly send an MQTT command with the payload 'getdb'
    to download the database.  We also can't test to see if the local
    database is current or what the current motion state is - we can really
    only respond to the sensor when it sends out a message.

    The device will broadcast messages on the following groups:
      group 01 = on (0x11) / off (0x13)
      group 03 = low battery (0x11) / good battery (0x13)
      group 04 = heartbeat (0x11)

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).  Supported signals are:

    - signal_on_off( Device, bool is_on ): Sent when the sensor is tripped
      (is_on=True) or resets (is_on=False).

    - signal_low_battery( Device, bool is_low ): Sent to indicate the current
      battery state.

    - signal_heartbeat( Device, True ): Sent when the device has broadcast a
      heartbeat signal.
    """
    type_name = "battery_sensor"

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

        # Sensor on/off signal.  API: func( Device, bool is_on )
        self.signal_on_off = Signal()
        # Sensor low battery signal.  API: func( Device, bool is_low )
        self.signal_low_battery = Signal()
        # Sensor heartbeat signal.  API: func( Device, True )
        self.signal_heartbeat = Signal()

        # Derived classes can override these or add to them.  Maps Insteon
        # groups to message type for this sensor.
        self.group_map = {
            # Sensor on/off activity on group 1.
            0x01 : self.handle_on_off,
            # Low battery is on group 3
            0x03 : self.handle_low_battery,
            # Heartbeat is on group 4
            0x04 : self.handle_heartbeat,
            }

        self._is_on = False

    #-----------------------------------------------------------------------
    def pair(self, on_done=None):
        """Pair the device with the modem.

        This only needs to be called one time.  It will set the device as a
        controller and the modem as a responder for all of the groups that
        the device can alert on.

        The device must already be a responder to the modem (push set on the
        modem, then set on the device) so we can update it's database.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("BatterySensor %s pairing", self.addr)

        # Build a sequence of calls to the do the pairing.  This insures each
        # call finishes and works before calling the next one.  We have to do
        # this for device db manipulation because we need to know the memory
        # layout on the device before making changes.
        seq = CommandSeq(self.protocol, "BatterySensor paired", on_done)

        # Start with a refresh command - since we're changing the db, it must
        # be up to date or bad things will happen.
        seq.add(self.refresh)

        # Add the device as a responder to the modem on group 1.  This is
        # probably already there - and maybe needs to be there before we can
        # even issue any commands but this check insures that the link is
        # present on the device and the modem.
        seq.add(self.db_add_resp_of, 0x01, self.modem.addr, 0x01,
                refresh=False)

        # Now add the device as the controller of the modem for groups 1-3.
        for group in range(1, 4):
            seq.add(self.db_add_ctrl_of, group, self.modem.addr, group,
                    refresh=False)

        # Finally start the sequence running.  This will return so the
        # network event loop can process everything and the on_done callbacks
        # will chain everything together.
        seq.run()

    #-----------------------------------------------------------------------
    def is_on(self):
        """Return if sensor has been tripped.
        """
        return self._is_on

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        """Handle broadcast messages from this device.

        A broadcast message is sent from the device when any activity is
        triggered.  This could be motion, low battery, etc.

        This callback will process the broadcast and emit the signals that
        correspond the events.

        Then the base class handle_broadcast() is called.  That will loop
        over every device that is linked to this device in the database and
        call handle_group_cmd() on those devices.  That insures that the
        devices that are linked to this device get updated to their correct
        states (Insteon devices don't send out a state change when the
        respond to a broadcast).

        Args:
          msg (InpStandard):  Broadcast message from the device.
        """
        # ACK of the broadcast - ignore this.
        if msg.cmd1 == 0x06:
            LOG.info("BatterySensor %s broadcast ACK grp: %s", self.addr,
                     msg.group)

        # On (0x11) and off (0x13) commands.
        elif msg.cmd1 == 0x11 or msg.cmd1 == 0x13:
            LOG.info("BatterySensor %s broadcast cmd %s grp: %s", self.addr,
                     msg.cmd1, msg.group)

            # Find the callback for this group and run that.
            handler = self.group_map.get(msg.group, None)
            if handler:
                handler(msg)
            else:
                LOG.error("BatterySensor no handler for group %s", msg.group)

            # This will find all the devices we're the controller of for this
            # group and call their handle_group_cmd() methods to update their
            # states since they will have seen the group broadcast and updated
            # (without sending anything out).
            super().handle_broadcast(msg)

        # If we haven't downloaded the device db yet, use this opportunity to
        # get the device db since we know the sensor is awake.  This doesn't
        # always seem to work, but it works often enough to be useful to try.
        if len(self.db) == 0:
            LOG.info("BatterySensor %s awake - requesting database", self.addr)
            self.refresh(force=True)

    #-----------------------------------------------------------------------
    def handle_on_off(self, msg):
        """Handle sensor activation.

        This is called by the device when a group broadcast on group 01 is
        sent out by the sensor.

        Args:
          msg (InpStandard):  Broadcast message from the device.
        """
        self._set_is_on(msg.cmd1 == 0x11)

    #-----------------------------------------------------------------------
    def handle_low_battery(self, msg):
        """Handle a low battery message.

        This is called by the device when a group broadcast on group 02 is
        sent out by the sensor.

        Args:
          msg (InpStandard):  Broadcast message from the device.  On/off is
              stored in msg.cmd1.
        """
        # Send True for low battery, False for regular.
        self.signal_low_battery.emit(msg.cmd1 == 0x11)

    #-----------------------------------------------------------------------
    def handle_heartbeat(self, msg):
        """Handle a heartbeat message.

        This is called by the device when a group broadcast on group 04 is
        sent out by the sensor.  Not all devices send heartbeats.

        Args:
          msg (InpStandard):  Broadcast message from the device.
        """
        # Send True for any heart beat message
        self.signal_heartbeat.emit(True)

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        """Handle replies to the refresh command.

        The refresh command reply will contain the current device
        state in cmd2 and this updates the device with that value.

        NOTE: refresh() will not work if the device is asleep.

        Args:
          msg (message.InpStandard):  The refresh message reply.  The current
              device state is in the msg.cmd2 field.
        """
        LOG.ui("BatterySensor %s refresh on = %s", self.addr, msg.cmd2 != 0x00)

        # Current on/off level is stored in cmd2 so update our state
        # to match.
        self._set_is_on(msg.cmd2 != 0x00)

    #-----------------------------------------------------------------------
    def _set_is_on(self, is_on):
        """Set the device on/off state.

        This will change the internal state and emit the state changed
        signal.

        Args:
          is_on (bool):  True if motion is active, False if it isn't.
        """
        LOG.info("Setting device %s on:%s", self.label, is_on)
        self._is_on = is_on
        self.signal_on_off.emit(self, self._is_on)

    #-----------------------------------------------------------------------
