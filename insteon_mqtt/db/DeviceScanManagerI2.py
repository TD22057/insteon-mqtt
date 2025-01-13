#===========================================================================
#
# Device Scan Manager for i2 or newer Devices
#
#===========================================================================
from .. import log
from .. import message as Msg
from .. import util
from .. import handler
from .DeviceEntry import DeviceEntry
from .Device import START_MEM_LOC

LOG = log.get_logger()


class DeviceScanManagerI2:
    """Manager for scaning the link database of an i2 or newer device.

    This class can be used to download any entries that failed to download
    using DeviceDbGet.py (or all entries, if started with a cleared DB).
    """
    def __init__(self, device, device_db, on_done=None, *, num_retry=3,
                 mem_addr: int = START_MEM_LOC):
        """Constructor

        Args
          device:  (Device) The Insteon Device object
          device_db: (db.Device) The device database being retrieved.
          on_done:   Finished callback.  Will be called when the scan
                     operation is done.
        Keyword-only Args:
          num_retry: (int) The number of times to retry each message if the
                     handler times out without returning Msg.FINISHED.
                     This count does include the initial sending so a
                     retry of 3 will send once and then retry 2 more times.
          mem_addr:  (int) Address at which to start downloading.
        """
        self.db = device_db
        self.device = device
        self._mem_addr = mem_addr
        self.on_done = util.make_callback(on_done)
        self._num_retry = num_retry

    #-------------------------------------------------------------------
    def start_scan(self):
        """Start a managed scan of a i2 (or newer) device database."""
        self._request_next_record(self.on_done)

    #-------------------------------------------------------------------
    def _request_next_record(self, on_done):
        """Request the next missing DB record.

        Args:
          on_done: (callback) a callback that is passed around and run on the
                   completion of the scan
        """

        done, last_entry = self._calculate_next_addr()
        if done:
            if self.db.is_complete():
                on_done(True, "Database received", last_entry)
            else:
                on_done(False, "Database incomplete", last_entry)
            return

        data = bytes([
            0x00,
            0x00,                   # ALDB record request
            self._mem_addr >> 8,    # Address MSB
            self._mem_addr & 0xff,  # Address LSB
            0x01,                   # Read one record
            ] + [0x00] * 9)
        msg = Msg.OutExtended.direct(self.device.addr, 0x2f, 0x00, data)
        msg_handler = handler.ExtendedCmdResponse(msg, self.handle_record,
                                                  on_done=on_done,
                                                  num_retry=self._num_retry)
        self.device.send(msg, msg_handler)

    #-------------------------------------------------------------------
    def handle_record(self, msg, on_done):
        """Handle an ALDB record response by adding an entry to the DB and
        fetching the next entry.

        Args:
          msg:     (message.InpExtended) The ALDB record response.
          on_done: (callback) a callback that is passed around and run on the
                   completion of the scan
        """

        # Convert the message to a database device entry.
        entry = DeviceEntry.from_bytes(msg.data, db=self.db)
        LOG.ui("Entry: %s", entry)

        # Skip entries w/ a null memory location.
        if entry.mem_loc:
            self.db.add_entry(entry)

        self._request_next_record(on_done)

    #-------------------------------------------------------------------
    def _calculate_next_addr(self) -> (bool, DeviceEntry):
        """Calculate the memory address of the next missing record.

        Returns:
          (bool) True if no more records to read
          (DeviceEntry) Last entry or closest-to-last (if not received yet)
        """
        done = False
        last = None
        addr = self._mem_addr
        entry = self.db.entries.get(addr, self.db.unused.get(addr, None))
        while entry is not None:
            last = entry
            if self.db.last.identical(entry):
                # This is the last record (and we already have it)
                done = True
                break
            addr -= 0x8
            entry = self.db.entries.get(addr, self.db.unused.get(addr, None))
        self._mem_addr = addr
        return done, last
