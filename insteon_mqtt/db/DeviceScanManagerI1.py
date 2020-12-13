#===========================================================================
#
# Device Scan Manager for i1 Devices
#
#===========================================================================
from .. import log
from .. import message as Msg
from .. import util
from .. import handler
from .DeviceEntry import DeviceEntry

LOG = log.get_logger()


class DeviceScanManagerI1:
    """Manager for scaning the link database of an i1 device.

       To download the all link database from an old i1 device, we have to send
       a series of requests.  All of these requests are standard length
       requests so the data payload is limited to 1 byte.  Since links are 8
       bytes this takes a while.  First we have to tell the device the most
       significant bit (MSB) of the address we want to start scanning from (0F
       in our case).  Then we have to request each least significant bit (LSB)
       to get the full link we do this using the peek command.

       Because the data payload is only 1 byte, there is no room for the
       "state" of the response message, meaning we will receive a single byte
       from the device, but the message will not have the address of the byte.
       So we have to track the state of the requests that we send, and if we
       are careful with how agressively we send our requests, we can be
       relatively certain that a response received is a response to the most
       recently sent message.  However, this can and will subtly fail at time.

       We detect the last message by parsing the full link data returned and
       looking for the high_water bit in the link record.

       This class will cache all of the bytes received until a full link record
       has been received, at which point it will pass the record onto the db
       handler.
    """
    def __init__(self, device, device_db, on_done=None, num_retry=3):
        """Constructor

        Args
          device:  (Device) The Insteon Device object
          device_db: (db.Device) The device database being retrieved.
          force:     (bool) If True, force a db download.  If False, only
                     download the db if it's out of date.
          on_done:   Finished callback.  Will be called when the scan
                     operation is done.
          num_retry: (int) The number of times to retry the message if the
                     handler times out without returning Msg.FINISHED.
                     This count does include the initial sending so a
                     retry of 3 will send once and then retry 2 more times.
        """
        self.db = device_db
        self.device = device
        self.record = []
        self.msb = None
        self.lsb = 0xF8
        self.on_done = util.make_callback(on_done)
        self._num_retry = num_retry

    #-------------------------------------------------------------------
    def start_scan(self):
        """Start a managed scan of a i1 device database
        """
        # Set the starting MSB
        self._set_msb(0x0F, self.on_done)

    #-------------------------------------------------------------------
    def _set_msb(self, msb, on_done):
        """Send the command to request the device to set the MSB

        Args
          msb:  The most significant bit value
        """
        self.msb = msb
        db_msg = Msg.OutStandard.direct(self.db.addr, 0x28, self.msb)
        msg_handler = handler.StandardCmd(db_msg, self.handle_set_msb,
                                          on_done=on_done,
                                          num_retry=self._num_retry)
        self.device.send(db_msg, msg_handler)

    #-------------------------------------------------------------------
    def handle_set_msb(self, msg, on_done):
        """Handle the device set msb response received from the device

        Make sure the msb byte received matches the one requested, otherwise
        resend the request.  If everything is in order, proceed to request
        the lsb.

        Args:
          msg:     (message.InpStandard) The msb message reply.  The msb
                   address requested is in the msg.cmd2 field.
          on_done: (callback) a callback that is passed around and run on the
                   completion of the scan
        """
        if msg.cmd2 == self.msb:
            LOG.info("%s device ACK Set MSB: %02x", msg.from_addr,
                     self.msb)
            db_msg = Msg.OutStandard.direct(self.db.addr, 0x2B,
                                            self.lsb)
            msg_handler = handler.StandardCmd(db_msg,
                                              self.handle_get_lsb,
                                              on_done=on_done,
                                              num_retry=self._num_retry)
            self.device.send(db_msg, msg_handler)
        else:
            LOG.warning("%s device ACK Set MSB had wrong value: %02x",
                        msg.from_addr, msg.cmd2)
            self._set_msb(self.msb, on_done)

    #-------------------------------------------------------------------
    def handle_get_lsb(self, msg, on_done):
        """Handle the device set lsb response received from the device

        LSB responses contain no state tracking, only the byte at the requested
        address.  The returned byte is cached here.

        If less than 8 bytes have been received, then request the next lsb
        address.

        If all 8 bytes of a link record have been received then send the
        cached pass it to the device to update it's database with the
        info.

        Args:
          msg:     (message.InpStandard) The lsb message reply.  The lsb data
                   is in the msg.cmd2 field.
          on_done: (callback) a callback that is passed around and run on the
                   completion of the scan
        """
        LOG.info("%s device received LSB Byte Value: %02x", msg.from_addr,
                 msg.cmd2)
        self.record.append(msg.cmd2)
        if len(self.record) == 8:
            # we have a full record, pass to db

            # Convert the message to a database device entry.
            entry = DeviceEntry.from_i1_bytes(bytes([self.msb, self.lsb] +
                                                    self.record), db=self.db)
            LOG.ui("Entry: %s", entry)
            self.db.add_entry(entry)

            # Empty our record cache
            self.record = []

            # Note the LAST bit and used bit are in the first byte
            # in other designs I have skipped reading the rest of
            # a record if these are found
            if entry.db_flags.is_last_rec:
                on_done(True, "Database received", entry)
                return

            #Jump down a distance of 2 records
            self.lsb -= 0x0F
        else:
            self.lsb += 1

        if self.lsb < 0:
            self.lsb = 0xF8
            self.msb -= 1
            # Request new MSB
            self._set_msb(self.msb, on_done)
        else:
            # Request the next LSB
            db_msg = Msg.OutStandard.direct(self.db.addr, 0x2B,
                                            self.lsb)
            msg_handler = handler.StandardCmd(db_msg,
                                              self.handle_get_lsb,
                                              on_done=on_done,
                                              num_retry=self._num_retry)
            self.device.send(db_msg, msg_handler)
