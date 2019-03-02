#===========================================================================
#
# SmokeBridge module
#
#===========================================================================
import enum
from .Base import Base
from ..CommandSeq import CommandSeq
from .. import log
from .. import message as Msg
from .. import handler
from ..Signal import Signal

LOG = log.get_logger()


class SmokeBridge(Base):
    """Insteon smoke detector bridge device.

    The smoke bridge connects wireless CO and smoke detectors into the
    Insteon network.  It will broadcast alerts for a series of conditions
    using different group numbers.  This requires pairing the modem as a
    responder for all of the groups that the smoke bridge uses.  The pair()
    method will do this automatically after the bridge is set as a responder
    to the modem (set modem, then bridge).

    Note: There is no way to ping the modem to find it's current alert state.
    If the alert is missed, there is no way to check to see what the status
    is.

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).  Supported signals are:

    - signal_on_off( Device, Type type, bool is_on ): Sent when the
      sensor changes state.  The type enumeration identifies the type of
      alert.
    """
    type_name = "smoke_bridge"

    # Broadcast group ID alert description
    class Type(enum.IntEnum):
        SMOKE = 0x01
        CO = 0x02
        TEST = 0x03
        CLEAR = 0x05
        LOW_BATTERY = 0x06
        ERROR = 0x07
        HEARTBEAT = 0x0A

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

        # State change notification signal.
        # API: func( Device, Type type, bool is_on )
        self.signal_on_off = Signal()

    #-----------------------------------------------------------------------
    def pair(self, on_done=None):
        """Pair the device with the modem.

        This only needs to be called one time.  It will set the device
        as a controller and the modem as a responder so the modem will
        see group broadcasts and report them to us.

        The device must already be a responder to the modem (push set
        on the modem, then set on the device) so we can update it's
        database.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Smoke bridge %s pairing", self.addr)

        # Build a sequence of calls to the do the pairing.  This insures each
        # call finishes and works before calling the next one.  We have to do
        # this for device db manipulation because we need to know the memory
        # layout on the device before making changes.
        seq = CommandSeq(self.protocol, "SmokeBridge paired", on_done)

        # Start with a refresh command - since we're changing the db, it must
        # be up to date or bad things will happen.
        seq.add(self.refresh)

        # Add the device as a responder to the modem on group 1.  This is
        # probably already there - and maybe needs to be there before we can
        # even issue any commands but this check insures that the link is
        # present on the device and the modem.
        seq.add(self.db_add_resp_of, 0x01, self.modem.addr, 0x01,
                refresh=False)

        # Now add the device as the controller of the modem for all the smoke
        # types.
        for type in SmokeBridge.Type:
            group = type.value
            seq.add(self.db_add_ctrl_of, group, self.modem.addr, group,
                    refresh=False)

        # Finally start the sequence running.  This will return so the
        # network event loop can process everything and the on_done callbacks
        # will chain everything together.
        seq.run()

    #-----------------------------------------------------------------------
    def refresh(self, force=False, on_done=None):
        """Refresh the current device state and database if needed.

        This sends a ping to the device.  Smoke bridge can't report it's
        current alert state but we can get the current all link db delta to
        check against our current db.  If the current db is out of date, it
        will trigger a download of the database.

        Args:
          force (bool):  If true, will force a refresh of the device database
                even if the delta value matches as well as a re-query of the
                device model information even if it is already known.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Smoke bridge %s cmd: status refresh", self.addr)

        seq = CommandSeq(self.protocol, "Device refreshed", on_done)

        # There is no way to get the current device status but we can request
        # the all link database delta so get that.  See smoke bridge dev
        # guide p25.  See the Base.refresh() comments for more details.
        msg = Msg.OutStandard.direct(self.addr, 0x1f, 0x01)
        msg_handler = handler.DeviceRefresh(self, self.handle_refresh, force,
                                            on_done, num_retry=3)
        seq.add_msg(msg, msg_handler)

        # If model number is not known, or force true, run get_model
        self.addRefreshData(seq, force)

        # Run all the commands.
        seq.run()

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        """Handle broadcast messages from this device.

        This is called automatically by the system (via handle.Broadcast)
        when we receive a message from the device.

        The broadcast message from a device is sent when the device is
        triggered.  The message has the group ID in it.  We'll update the
        device state and look up the group in the all link database.  For
        each device that is in the group (as a reponsder), we'll call
        handle_group_cmd() on that device to trigger it.  This way all the
        devices in the group are updated to the correct values when we see
        the broadcast message.

        Args:
          msg (InpStandard):  Broadcast message from the device.
        """
        # ACK of the broadcast - ignore this.
        if msg.cmd1 == 0x06:
            LOG.info("Smoke bridge %s broadcast ACK grp: %s", self.addr,
                     msg.group)

        # 0x11 ON command for the smoke bridge means the error is active.
        # NOTE: there is no off command - that seems to be handled by the
        # bridge sending the CLEAR condition group.
        elif msg.cmd1 == 0x11:
            LOG.info("Smoke bridge %s broadcast ON grp: %s", self.addr,
                     msg.group)

            try:
                type = SmokeBridge.Type(msg.group)
            except TypeError:
                LOG.exception("Unknown smoke bridge group %s.", msg.group)
                return

            LOG.info("Smoke bridge %s signaling condition %s", self.addr, type)

            # Unlike most devices, there is no "off" state for the errors.
            # The different types (SMOKE, CO, etc) indicate that an alert is
            # active.  A Type of CLEAR indicates that the alerts are all off.
            if type != SmokeBridge.Type.CLEAR:
                self.signal_on_off.emit(self, type, True)
            else:
                for type in SmokeBridge.Type:
                    if type == SmokeBridge.Type.CLEAR:
                        continue

                    self.signal_on_off.emit(self, type, False)

            # As long as there is no errors (which return above), call
            # handle_broadcast for any device that we're the controller of.
            super().handle_broadcast(msg)

    #-----------------------------------------------------------------------
