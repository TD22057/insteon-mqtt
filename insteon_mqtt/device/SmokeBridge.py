#===========================================================================
#
# SmokeBridge module
#
#===========================================================================
import logging
from .Base import Base
from .. import message as Msg
from .. import handler
from ..Signal import Signal

LOG = logging.getLogger(__name__)


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

    # broadcast group -> alert description
    conditions = {
        0x01 : 'smoke',
        0x02 : 'CO',
        0x03 : 'test',
        0x05 : 'clear',
        0x06 : 'low battery',
        0x07 : 'error',
        0x0a : 'heartbeat',
        }

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

        # emit(device, condition)
        self.signal_state_change = Signal()

    #-----------------------------------------------------------------------
    def pair(self):
        """Pair the device with the modem.

        This only needs to be called one time.  It will set the device
        as a controller and the modem as a responder for all of the
        groups that the device can alert on.

        The device must already be a responder to the modem (push set
        on the modem, then set on the device) so we can update it's
        database.
        """
        LOG.info("Smoke bridge %s pairing", self.addr)

        # Search our db to see if we have controller links for all our
        # groups back to the modem.  If one doesn't exist, add it on
        # our device and the modem.
        add_groups = []
        for group in SmokeBridge.conditions.keys():
            if not self.db.find(self.modem.addr, group, True):
                LOG.info("Smoke bridge adding ctrl for group %s", group)
                self.db_add_ctrl_of(self.modem.addr, group)

    #-----------------------------------------------------------------------
    def refresh(self):
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
        msg_handler = handler.DeviceRefresh(self, msg, num_retry=3)
        self.protocol.send(msg, msg_handler)

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

        # 0x11 ON command for the smoke bridge means the error is active.
        elif msg.cmd1 == 0x11:
            LOG.info("Smoke bridge %s broadcast ON grp: %s", self.addr,
                     msg.group)

            condition = self.conditions.get(msg.group, None)
            if condition:
                LOG.info("Smoke bridge %s signaling group %s", self.addr,
                         msg.group)
                self.signal_state_change.emit(self, condition)
            else:
                LOG.info("Smoke bridge %s ignoring group %s", self.addr,
                         msg.group)

        # Call handle_broadcast for any device that we're the
        # controller of.
        super().handle_broadcast(msg)

    #-----------------------------------------------------------------------
