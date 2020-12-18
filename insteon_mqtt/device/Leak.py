#===========================================================================
#
# Insteon leak sensor
#
#===========================================================================
from .BatterySensor import BatterySensor
from ..CommandSeq import CommandSeq
from .. import log
from ..Signal import Signal

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
      group 01 = wet condition
      group 02 = dry condition
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

        # Wet/dry signal.  API: func( Device, bool is_wet )
        self.signal_wet = Signal()

        # Maps Insteon groups to message type for this sensor.
        self.group_map = {
            # Dry event on group 1.
            0x01 : self.handle_dry,
            # Wet event on group 2.
            0x02 : self.handle_wet,
            # Heartbeat is on group 4
            0x04 : self.handle_heartbeat,
            }

        self._is_wet = False

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
        LOG.info("LeakSensor %s pairing", self.addr)

        # Build a sequence of calls to the do the pairing.  This insures each
        # call finishes and works before calling the next one.  We have to do
        # this for device db manipulation because we need to know the memory
        # layout on the device before making changes.
        seq = CommandSeq(self, "LeakSensor paired", on_done, name="DevPair")

        # Start with a refresh command - since we're changing the db, it must
        # be up to date or bad things will happen.
        seq.add(self.refresh)

        # Add the device as a responder to the modem on group 1.  This is
        # probably already there - and maybe needs to be there before we can
        # even issue any commands but this check insures that the link is
        # present on the device and the modem.
        # This link handle the dry event
        seq.add(self.db_add_resp_of, 0x01, self.modem.addr, 0x01,
                refresh=False)

        # This link handle the wet event
        seq.add(self.db_add_ctrl_of, 0x02, self.modem.addr, 0x02,
                refresh=False)

        # This link handle the heartbeat event
        seq.add(self.db_add_ctrl_of, 0x04, self.modem.addr, 0x04,
                refresh=False)

        # Finally start the sequence running.  This will return so the
        # network event loop can process everything and the on_done callbacks
        # will chain everything together.
        seq.run()

    #-----------------------------------------------------------------------
    def handle_dry(self, msg):
        """Handle a dry message.

        This is called by the device when a leak is cleared and the device is
        dry.

        Args:
          msg (InpStandard):  Broadcast message from the device.
        """
        LOG.info("LeakSensor received is-dry message")
        self._set_is_wet(False)

    #-----------------------------------------------------------------------
    def handle_wet(self, msg):
        """Handle a wet message.

        This is called by the device when a leak is detected and the device
        is wet.

        Args:
          msg (InpStandard):  Broadcast message from the device.
        """
        LOG.info("LeakSensor received is-wet message")
        self._set_is_wet(True)

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
        # Update the wet/dry state using the heartbeat if needed.
        is_wet = msg.cmd1 == 0x13
        if self._is_wet != is_wet:
            self._set_is_wet(is_wet)

        # Send True for any heart beat message
        self.signal_heartbeat.emit(self, True)

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        """Callback for handling refresh() responses.

        This is called when we get a response to the refresh() command.  The
        refresh command reply will contain the current device state in cmd2
        and this updates the device with that value.  It is called by
        handler.DeviceRefresh when we can an ACK for the refresh command.

        NOTE: refresh() will not work if the device is asleep.

        Args:
          msg (message.InpStandard):  The refresh message reply.  The current
              device state is in the msg.cmd2 field.
        """
        LOG.ui("LeakSensor %s refresh on = %s", self.addr, msg.cmd2 != 0x00)

        # Current wet/dry level is stored in cmd2.  Non-zero == wet.
        self._set_is_wet(msg.cmd2 != 0x00)

    #-----------------------------------------------------------------------
    def _set_is_wet(self, is_wet):
        """Update the device wet/dry state.

        This will change the internal state and emit the state changed
        signals.  It is called by whenever we're informed that the device has
        changed state.

        Args:
          is_wet (bool):  True if Leak is detected, False if it isn't.
        """
        LOG.info("Setting device %s on:%s", self.label, is_wet)
        self._is_wet = is_wet

        self.signal_wet.emit(self, self._is_wet)

    #-----------------------------------------------------------------------
