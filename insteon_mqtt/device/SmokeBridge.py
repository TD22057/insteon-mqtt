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

        # Update the group map with the groups to be paired and the handler
        # for broadcast messages from this group
        self.group_map.update({self.Type.SMOKE.value: self.handle_message,
                               self.Type.CO.value: self.handle_message,
                               self.Type.TEST.value: self.handle_message,
                               self.Type.CLEAR.value: self.handle_message,
                               self.Type.LOW_BATTERY.value:
                               self.handle_message,
                               self.Type.ERROR.value: self.handle_message,
                               self.Type.HEARTBEAT.value: self.handle_message,
                               })

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

        seq = CommandSeq(self, "Device refreshed", on_done, name="DevRefresh")

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
    def handle_message(self, msg):
        """Handle broadcast messages from this device.

        This is called by Base.handle_broadcast using the group_map map.

        Args:
          msg (InpStandard):  Broadcast message from the device.
        """
        # ACK of the broadcast - ignore this.
        if msg.cmd1 == Msg.CmdType.LINK_CLEANUP_REPORT:
            LOG.info("Smoke bridge %s broadcast ACK grp: %s", self.addr,
                     msg.group)

        # 0x11 ON command for the smoke bridge means the error is active.
        # NOTE: there is no off command - that seems to be handled by the
        # bridge sending the CLEAR condition group.
        elif msg.cmd1 == Msg.CmdType.ON:
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
            self.update_linked_devices(msg)

    #-----------------------------------------------------------------------
