#===========================================================================
#
# Insteon leak sensor
#
#===========================================================================
from .Base import Base
from ..CommandSeq import CommandSeq
from .. import log
from ..Signal import Signal

LOG = log.get_logger()


class Leak(Base):
    """Insteon battery powered water leak sensor.

    A leak sensor is basically an on/off sensor except that it's
    batter powered and only awake when water is detected or the set
    button is pressed.  It will broadcast an on command for group 1
    when dry and on command for group 2 when wet. It will also broadcast
    a heartbeat signal every 24 hours on group 4.

    The issue with a battery powered sensor is that we can't download
    the link database without the sensor being on.  You can trigger
    the sensor manually and then quickly send an MQTT command with the
    payload 'getdb' to download the database.  We also can't test to
    see if the local database is current or what the current motion
    state is - we can really only respond to the sensor when it sends
    out a message.

    The Signal Leak.signal_active(True) will be emitted whenever the
    device senses water and signal_active(False) when no water is detected.

    TODO: download the database automatically when leak/heartbeat is seen.
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
        self.signal_heartbeat = Signal()  # (Device, bool)

        # Maps Insteon groups to message type for this sensor.
        self.group_map = {
            # Dry event on group 1.
            0x01 : self.handle_dry,
            # Wet event on group 2.
            0x02 : self.handle_wet,
            # Heartbeat is on group 4
            0x04 : self.handle_heartbeat,
            }

        self._is_on = False

    #-----------------------------------------------------------------------
    def pair(self, on_done=None):
        """Pair the device with the modem.

        This only needs to be called one time. For the leak sensors, we don't
        need to add more CTRL/RESP pair beside the standard group 1 pair.

        The device must already be a responder to the modem (push set
        on the modem, then set on the device) so we can update it's
        database.
        """
        LOG.info("LeakSensor %s pairing", self.addr)

        # Build a sequence of calls to the do the pairing.  This insures each
        # call finishes and works before calling the next one.  We have to do
        # this for device db manipulation because we need to know the memory
        # layout on the device before making changes.
        seq = CommandSeq(self.protocol, "LeakSensor paired", on_done)

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
    def is_on(self):
        """Return if sensor has been tripped.
        """
        return self._is_on

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        """Handle broadcast messages from this device.

        The broadcast message from a device is sent when the device is
        triggered and when the leak return to dry.  The message has the
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
            LOG.info("LeakSensor %s broadcast ACK grp: %s", self.addr,
                     msg.group)
            # Use this opportunity to get the device db since we know the
            # sensor is awake.
            if len(self.db) == 0:
                LOG.info("LeakSensor %s awake - requesting database",
                         self.addr)
                self.refresh(force=True)
            return

        # On (0x11) and off (0x13) commands.
        elif msg.cmd1 == 0x11 or msg.cmd1 == 0x13:
            LOG.info("LeakSensor %s broadcast cmd %s grp: %s", self.addr,
                     msg.cmd1, msg.group)

            handler = self.group_map.get(msg.group, None)
            if handler:
                handler(msg)
            else:
                LOG.error("LeakSensor no handler for group %s", msg.group)

        # Broadcast to the devices we're linked to. Call
        # handle_broadcast for any device that we're the controller of.
        super().handle_broadcast(msg)

        # Use this opportunity to get the device db since we know the
        # sensor is awake.
        if len(self.db) == 0:
            LOG.info("LeakSensor %s awake - requesting database", self.addr)
            self.refresh(force=True)

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

        # Send True for any heart beat message
        self.signal_heartbeat.emit(self, True)

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
        LOG.ui("LeakSensor %s refresh on = %s", self.addr, msg.cmd2 != 0x00)

        # Current on/off level is stored in cmd2 so update our state
        # to match.
        self._set_is_on(msg.cmd2 != 0x00)

    #-----------------------------------------------------------------------
    def _set_is_on(self, is_on):
        """Set the device on/off state.

        This will change the internal state and emit the state changed
        signal.

        Args:
          is_on:   (bool) True if Leak is detected, False if it isn't.
        """
        LOG.info("Setting device %s on:%s", self.label, is_on)
        self._is_on = is_on
        self.signal_active.emit(self, self._is_on)

    #-----------------------------------------------------------------------
