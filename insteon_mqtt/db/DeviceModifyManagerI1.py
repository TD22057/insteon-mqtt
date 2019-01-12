#===========================================================================
#
# Device DB Entry Modify Manager for i1 Devices
#
#===========================================================================
from .. import log
from .. import message as Msg
from .. import util
from .. import handler

LOG = log.get_logger()


class DeviceModifyManagerI1:
    """Manager for modifying the link database of an i1 device.

       To maninpulate the all link database from an old i1 device, we have to
       send a series of requests.  All of these requests are standard length
       requests so the data payload is limited to 1 byte.  Since links are 8
       bytes this takes a while.  First we have to tell the device the most
       significant bit (MSB) of the address we want to start scanning from (0F
       in our case).  Then we have to peek and poke each least significant bit
       (LSB) byte into place.

       Because the data payload is only 1 byte, this gets stupid fast.  First,
       we have to peek the least significant byte.  The device then responds
       with a peel response message that contains the byte at that location,
       but not the address of the byte. So we have to track the state of the
       requests that we send, and if we are careful with how agressively we
       send our requests, we can be relatively certain that a response received
       is a response to the most recently sent message.

       Second, in order to write to that address, we poke a single byte back to
       the device.  This request lacks any details about the address, instead
       the device writes the data to the last peeked byte.  The device responds
       with an ack containing the value of the poked byte.

       This is a fragile process, amazingly it works most of the time.
       However, this can and will subtly fail at time.  In some instances,
       there is no indication of the failure other than an improperly written
       link on the device.

       This class is initialized with the full entry to write to the device
       and handles the management of sending the necessary commands to write
       the link to the device.  The class only writes the bytes that need to be
       changed.
    """

    #-------------------------------------------------------------------
    def __init__(self, device, device_db, i1_entry, on_done=None,
                 num_retry=3):
        """Constructor

        Args
          device:    (Device) The Insteon Device object
          device_db: (db.Device) The device database being manipulated.
          i1_entry:  (bytes) 10 byte array of the i1_entry
          on_done:   Finished callback.  Will be called when the modify
                     operation is done.
          num_retry: (int) The number of times to retry the message if the
                     handler times out without returning Msg.FINISHED.
                     This count does include the initial sending so a
                     retry of 3 will send once and then retry 2 more times.
        """
        self.db = device_db
        self.device = device
        self.record = i1_entry[2:10]
        self.record_index = 0
        self.msb = i1_entry[0]
        self.lsb = i1_entry[1]  # this is the end address
        self.on_done = util.make_callback(on_done)
        self._num_retry = num_retry

    #-------------------------------------------------------------------
    def start_modify(self, on_done=None):
        """Start a managed manipulation of a i1 device database

        Args:
          on_done: Finished callback to be called when the modify entire
                   operation is done.  If not NONE it will replace the
                   the on_done specified in the __init__()
        """
        if on_done is not None:
            self.on_done = util.make_callback(on_done)
        # Set the starting MSB
        self._set_msb(self.msb)

    #-------------------------------------------------------------------
    def _set_msb(self, msb):
        """Send the command to request the device to set the MSB

        Args
          msb:  The most significant bit value
        """
        self.msb = msb
        db_msg = Msg.OutStandard.direct(self.db.addr, 0x28, self.msb)
        msg_handler = handler.StandardCmd(db_msg, self.handle_set_msb,
                                          on_done=self.on_done,
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
                   completion of the modification
        """
        if msg.cmd2 == self.msb:
            LOG.info("%s device ACK Set MSB: %02x", msg.from_addr,
                     self.msb)
            self.get_next_lsb(on_done)
        else:
            LOG.warning("%s device ACK Set MSB had wrong value: %02x",
                        msg.from_addr, msg.cmd2)
            self._set_msb(self.msb)

    #-------------------------------------------------------------------
    def handle_lsb_response(self, msg, on_done):
        """Handle the device set lsb or write lsb response received from the
        device

        LSB responses contain no state tracking, only the byte at the requested
        address, or the byte that was written to the address.  If the returned
        byte matches the byte we are supposed to write then either we
        successfully wrote the byte, or we don't even need to write the
        byte at all.

        Args:
          msg:     (message.InpStandard) The lsb message reply.  The lsb data
                   is in the msg.cmd2 field.
          on_done: (callback) a callback that is passed around and run on the
                   completion of the modification
        """
        LOG.info("%s device received LSB Byte Value: %02x", msg.from_addr,
                 msg.cmd2)

        if msg.cmd2 != self.record[self.record_index]:
            self.write_lsb_byte(on_done)
        else:
            self.advance_lsb(on_done)

    #-------------------------------------------------------------------
    def write_lsb_byte(self, on_done):
        """Writes the next byte in the record to the device.

        Uses the device poke_byte command.  The next byte is the byte in the
        self.record_index position in self.record

        Args:
          on_done: (callback) a callback that is passed around and run on the
                   completion of the modification
        """
        db_msg = Msg.OutStandard.direct(self.db.addr, 0x29,
                                        self.record[self.record_index])
        msg_handler = handler.StandardCmd(db_msg,
                                          self.handle_lsb_response,
                                          on_done=on_done,
                                          num_retry=self._num_retry)
        self.device.send(db_msg, msg_handler)

    #-------------------------------------------------------------------
    def advance_lsb(self, on_done):
        """Is Another LSB Required, If so Request it.

        Looks at the record and to determine if more bytes need to be written.
        If this is an unused record, only need to write the firs byte which
        is the flag.

        If additional bytes need to be written the process is continued, if
        no additinal bytes need to be written, the on_done function is called.

        Args:
          on_done: (callback) a callback that is passed around and run on the
                   completion of the modification
        """
        if self.record_index == 0:
            flags = Msg.DbFlags.from_bytes(self.record)
            if not flags.in_use:
                # We are done
                on_done(True, "Database entry written", None)
                return

        if self.record_index == 7:
            # We are done
            on_done(True, "Database entry written", None)
        else:
            # Still more to go, bump up record index and continue
            self.record_index += 1
            self.get_next_lsb(on_done)

    #-------------------------------------------------------------------
    def get_next_lsb(self, on_done):
        """Send the next peek request to the device.

        LSB is calculated by using the high lsb position minus 7 plus the
        current self.record_index

        Args:
          on_done: (callback) a callback that is passed around and run on the
                   completion of the modification
        """
        db_msg = Msg.OutStandard.direct(self.db.addr, 0x2B,
                                        self.lsb - 7 + self.record_index)
        msg_handler = handler.StandardCmd(db_msg,
                                          self.handle_lsb_response,
                                          on_done=on_done,
                                          num_retry=self._num_retry)
        self.device.send(db_msg, msg_handler)
