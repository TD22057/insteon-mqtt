#===========================================================================
#
# Device refresh (ping) command handler.
#
#===========================================================================
from .. import log
from .. import message as Msg
from .. import db
from .Base import Base
from .DeviceDbGet import DeviceDbGet


LOG = log.get_logger()


class DeviceRefresh(Base):
    """Refresh the state and database version of a device handler.

    This handles device refresh messages.  Some devices don't respond very
    well (look at you SmokeBridge) so the handler has a built in retry system
    to resend the initial message if the handler times out.

    When a response arrives, device.handle_refresh(msg) is called to extract
    the current state of the device (on/off, dimmer level, etc).
    Additionally, we'll check the device's database delta version to see if
    the database needs to re-downloaded from the device.  If it does, the
    handler will send a new message to request the database.
    """
    def __init__(self, device, callback, force, on_done=None, num_retry=3,
                 skip_db=False):
        """Constructor

        Args
          device (Device):  The Insteon device.
          callback:  Callback function to call when the reply arrives.  API:
                     callback( Msg.InpStandard )
          force (bool):  If True, force a db download.  If False, only
                download the db if it's out of date.
          on_done:  Finished callback.  Will be called when the refresh
                    operation is done.
          num_retry (int):  The number of times to retry the message if the
                    handler times out without returning Msg.FINISHED.
                    This count does include the initial sending so a
                    retry of 3 will send once and then retry 2 more times.
          skip_db (bool):  If True, ignore the database version and don't
                  download the database.
        """
        super().__init__(on_done, num_retry)

        self.device = device
        self.callback = callback
        self.force = force
        self.skip_db = skip_db
        self.addr = device.addr

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        Args:
          protocol (Protocol):  The Insteon Protocol object
          msg:  Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        # Probably an echo back of our sent message.
        if isinstance(msg, Msg.OutStandard) and msg.to_addr == self.addr:
            if msg.is_ack:
                LOG.debug("%s ACK response", self.addr)
                return Msg.CONTINUE
            else:
                LOG.error("%s NAK response", self.addr)
                self.on_done(False, "NAK response", None)
                return Msg.FINISHED

        # See if this is the standard message ack/nak we're expecting.
        elif isinstance(msg, Msg.InpStandard) and msg.from_addr == self.addr:
            # Since we got the message we expected, turn off retries.
            self.stop_retry()

            # All link database delta is stored in cmd1 so we if we have the
            # latest version.  If not, schedule an update.
            need_refresh = True
            if self.skip_db:
                need_refresh = False
            elif not self.force and self.device.db.is_current(msg.cmd1):
                LOG.ui("Device database is current at delta %s", msg.cmd1)
                need_refresh = False

            # Call the device refresh handler.  This sets the current device
            # state which is usually stored in cmd2.
            self.callback(msg)

            if not need_refresh:
                self.on_done(True, "Refresh complete", None)
            else:
                LOG.ui("Device %s db out of date (got %s vs %s), refreshing",
                       self.addr, msg.cmd1, self.device.db.delta)

                # Clear the current database values.
                self.device.db.clear()

                # When the update message below ends, update the db delta w/
                # the current value and save the database.
                def on_done(success, message, data):
                    if success:
                        self.device.db.set_delta(msg.cmd1)
                        LOG.ui("%s database download complete\n%s",
                               self.addr, self.device.db)
                    self.on_done(success, message, data)

                # Request that the device send us all of it's database
                # records.  These will be streamed as fast as possible to us
                # and the handler will update the database.  We need a retry
                # count here because battery powered devices don't always
                # respond right away.
                if self.device.db.engine == 0:
                    scan_manager = db.DeviceScanManagerI1(self.device,
                                                          self.device.db,
                                                          on_done=on_done,
                                                          num_retry=3)
                    scan_manager.start_scan()
                else:
                    db_msg = Msg.OutExtended.direct(self.addr, 0x2f, 0x00,
                                                    bytes(14))
                    msg_handler = DeviceDbGet(self.device.db, on_done,
                                              num_retry=3)
                    self.device.send(db_msg, msg_handler)

            # Either way - this transaction is complete.
            return Msg.FINISHED

        # Unknown message - not for us.
        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
