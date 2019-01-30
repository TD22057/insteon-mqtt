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
    """Insteon Smoke Bridge

    The smoke bridge connects wireless CO and smoke detectors into the
    Insteon network.  It will broadcast alerts for a series of
    conditions using different group numbers.  This requires pairing
    the modem as a responder for all of the groups that the smoke
    bridge uses.  The pair() method will do this automatically after
    the bridge is set as a responder to the modem (set modem, then
    bridge).

    Note: There is no way to ping the modem to find it's current alert
    state.  If the alert is missed, there is no way to check to see
    what the status is.

    When the smoke bridge alert is triggered, it will emit a signal
    using SmokeBridge.signal_state_change with a condition string
    (SmokeBridge.conditions) of the alert.

    Sample configuration input:

        insteon:
          devices:
            - smoke_bridge:
              address: 44.a3.79
    """
    type_name = "smoke_bridge"

    # broadcast group ID alert description
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
          protocol:    (Protocol) The Protocol object used to communicate
                       with the Insteon network.  This is needed to allow
                       the device to send messages to the PLM modem.
          modem:       (Modem) The Insteon modem used to find other devices.
          address:     (Address) The address of the device.
          name         (str) Nice alias name to use for the device.
        """
        super().__init__(protocol, modem, address, name)

        self.signal_state_change = Signal()  # emit(device, Type type)

    #-----------------------------------------------------------------------
    def pair(self, on_done=None):
        """Pair the device with the modem.

        This only needs to be called one time.  It will set the device
        as a controller and the modem as a responder for all of the
        groups that the device can alert on.

        The device must already be a responder to the modem (push set
        on the modem, then set on the device) so we can update it's
        database.
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

        This sends a ping to the device.  Smoke bridge can't report
        it's current alert state but we can get the current all link
        db delta to check against our current db.  If the current db
        is out of date, it will trigger a download of the database.
        """
        LOG.info("Smoke bridge %s cmd: status refresh", self.addr)

        # There is no way to get the current device status but we can
        # request the all link database delta so get that.  See smoke
        # bridge dev guide p25.  See the Base.refresh() comments for
        # more details.
        msg = Msg.OutStandard.direct(self.addr, 0x1f, 0x01)
        msg_handler = handler.DeviceRefresh(self, self.handle_refresh, force,
                                            on_done, num_retry=3)
        self.send(msg, msg_handler)

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

        Smoke bridge will emit the SmokeBridge.signal_state_change
        signal with the alert condition string whenever the bridge
        sends out a broadcast message.

        Args:
          msg:   (InptStandard) Broadcast message from the device.
        """
        # ACK of the broadcast - ignore this.
        if msg.cmd1 == 0x06:
            LOG.info("Smoke bridge %s broadcast ACK grp: %s", self.addr,
                     msg.group)
            return

        # 0x11 ON command for the smoke bridge means the error is
        # active.  NOTE: there is no off command - that seems to be
        # handled by the bridge sending the CLEAR condition group.
        if msg.cmd1 == 0x11:
            LOG.info("Smoke bridge %s broadcast ON grp: %s", self.addr,
                     msg.group)

            try:
                condition = SmokeBridge.Type(msg.group)
            except TypeError:
                LOG.exception("Unknown smoke bridge group %s.", msg.group)
                return

            LOG.info("Smoke bridge %s signaling condition %s", self.addr,
                     condition)
            self.signal_state_change.emit(self, condition)

        # As long as there is no errors (which return above), call
        # handle_broadcast for any device that we're the controller
        # of.
        super().handle_broadcast(msg)

    #-----------------------------------------------------------------------
