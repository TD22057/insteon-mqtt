#===========================================================================
#
# Network link to a Serial device class
#
#===========================================================================
import serial
from .. import log
from ..Signal import Signal
from .Link import Link

LOG = log.get_logger(__name__)


class Serial(Link):
    """Serial network link.

    This class reads and writes to a serial connection using the pyserial
    module.  This class adapts the serial package to use the network manager
    class to allow for multiple connections and other network activity to
    occur.

    Data reading and writing is handled via the Signal clsas.  When data is
    read, Serial.signal_read(Serial, bytes) will be emitted with the link and
    the data that was read.  When data is successfully written,
    Serial.signal_write(Serial, bytes) will be called with the data that was
    written.

    Input fields can be set via the constructor or by loading a configuration
    file (see load_config for details).
    """
    read_buf_size = 4096
    max_write_queue = 500

    #-----------------------------------------------------------------------
    def __init__(self, port=None, baudrate=19200, parity=serial.PARITY_NONE,
                 reconnect_dt=10):
        """Constructor.

        The client will not be connected until connect() is called.
        Either manually or by the network manager.

        Args:
          port (str):  The serial device or URL to connect to.  See
                       the serial.serial_for_url() documentation for details.
          baudrate (int):  Baud rate to use in the connection.
          parity:  serial.PARITY value to use.
          reconnect_dt (int): Time in seconds to try and reconnect if the
                       connection drops.

        """
        # Public signals to connect to for read/write notification.
        self.signal_read = Signal()   # (Serial, bytes)
        self.signal_wrote = Signal()  # (Serial, bytes)

        super().__init__()

        self._port = port
        self._baudrate = baudrate
        self._parity = parity
        self._reconnect_dt = reconnect_dt
        self._fd = None

        # List of packets to write.  Each is a tuple of (bytes, time) where
        # the time is the time after which to do the write.
        self._write_buf = []

        # Create the serial client but don't open it yet.  We'll wait for a
        # connection call to do that.
        self.client = None
        if port:
            self._open_client()

        self.signal_connected.connect(self._connected)

    #-----------------------------------------------------------------------
    def load_config(self, config):
        """Load a configuration dictionary.

        Configuration inputs will override any set in the constructor.

        The input configuration dictionary can contain:
        - port (str):  The serial device to connect to.
        - baudrate (int):  Baudrate to use (optional)
        - parity:  Parity to use (optional)

        Args:
          config (dict):  Configuration data to load.
        """
        assert self._fd is None

        self._port = config.get('port', self._port)
        self._baudrate = config.get('baudrate', self._baudrate)
        self._parity = config.get('parity', self._parity)

        self.client = self._open_client()

    #-----------------------------------------------------------------------
    def fileno(self):
        """Return the file descriptor to watch for this link.

        Returns:
          int:  Returns the descriptor (obj.fileno() usually) to monitor.
        """
        assert self._fd
        return self._fd

    #-----------------------------------------------------------------------
    def write(self, data, after_time=None):
        """Schedule data for writing to the serial device.

        This pushes the data into a queue for writing to the serial device.
        Only after the network event loop flags the device for writing will
        it actually be written.

        Args:
          after_time (float):  Time in seconds past epoch after which to write
                     the packet.  If None, the message will be sent whenever
                     it can.
        """
        # Default after time is 0 which will always write.
        after_time = after_time if after_time is not None else 0

        # Save the input data to the write queue.
        self._write_buf.append((data, after_time))
        self.signal_needs_write.emit(self, True)

        # if we have exceed the max queue size, pop the oldest packet off.
        # This way if the link goes down for a long time, we don't just build
        # up a infinite number of packets to write.
        if (Serial.max_write_queue and
                len(self._write_buf) > Serial.max_write_queue):
            self._write_buf.pop(0)

    #-----------------------------------------------------------------------
    def retry_connect_dt(self):
        """Return a positive integer (seconds) if the link should reconnect.

        If this returns None, the link will not be reconnected if it
        closes.  Otherwise this is the retry interval in seconds to
        try and reconnect the link by calling connect().
        """
        return self._reconnect_dt

    #-----------------------------------------------------------------------
    def connect(self):
        """Connect the link to the device.

        This will try and connect to the serial port.

        Returns:
          bool:  Returns True if the connection was successful or False it
          it failed.
        """
        try:
            # Try and open the client and get the file descriptor.
            self.client.open()
            self._fd = self.client.fileno()

            LOG.info("Serial device opened %s", self.client.port)
            return True
        except:
            LOG.exception("Serial connection error to %s", self.client.port)
            return False

    #-----------------------------------------------------------------------
    def read_from_link(self):
        """Read data from the link.

        This will be called by the manager when there is data available on
        the file descriptor for reading.

        Returns:
           int:  Return -1 if the link should be closed.  Or any other
           integer to indicate success.
        """
        try:
            # Read from the file descriptor.
            data = self.client.read(self.read_buf_size)
            if data:
                #LOG.debug("Read %s bytes from serial %s: %s", len(data),
                #               self.client.port, data)

                # Send the data out via signal call.
                self.signal_read.emit(self, data)
        except:
            LOG.exception("Serial read error from %s", self.client.port)

    #-----------------------------------------------------------------------
    def write_to_link(self, t):
        """Write data from the link.

        This will be called by the manager when the file descriptor can be
        written to.  It will only be called after the link as emitted the
        signal_needs_write(True).  Once all the data has been written, the
        link should call self.signal_needs_write.emit(False).

        Args:
           t (float:  The current time (time.time).
        """
        # If there is no more data to write, remove us from the write
        # watching.
        if not self._write_buf:
            self.signal_needs_write.emit(self, False)
            return

        # Get the next data packet to write from the write queue and see if
        # enough time has elapsed to write the message.
        data, after_time = self._write_buf[0]
        if t < after_time:
            #LOG.debug("Waiting to write %f < %f", t, after_time)
            return

        try:
            # Write as much of that data as possible.
            num = self.client.write(data)
            LOG.debug("Wrote %s bytes to serial %s", num, self.client.port)

            if num == len(data):
                # If we wrote the whole packet, pop it off the queue.
                self._write_buf.pop(0)

                # Remove us from the write watcher if there is no more data
                # to write.
                if len(self._write_buf) == 0:
                    self.signal_needs_write.emit(self, False)

                # Signal that the packet was written.
                self.signal_wrote.emit(self, data)

            elif num:
                # Still data to write - remove the written data from the
                # buffer.
                self._write_buf[0] = data[num:]

        except:
            LOG.exception("Serial write error from %s", self.client.port)

    #-----------------------------------------------------------------------
    def close(self):
        """Close the link.

        The link will call self.signal_closing.emit() after closing.
        """
        if not self._fd:
            return

        LOG.info("Serial device closing %s", self.client.port)

        self.client.close()
        self._fd = None
        self._write_buf = []
        self.signal_closing.emit(self)

    #-----------------------------------------------------------------------
    def _open_client(self):
        """Create the serial client.

        The connection is not actually opened yet - that happens in
        connect().
        """
        client = serial.serial_for_url(self._port, do_not_open=True, timeout=0,
                                       write_timeout=0)
        client.baudrate = self._baudrate
        client.parity = self._parity
        return client

    #-----------------------------------------------------------------------
    def _connected(self, link, connected):
        """Connected callback.

        This is called after the device connects.  If we have data remaining
        to write, we'll notify the manager of that.  This way data can be
        written to the device before it's open or when we're disconnected and
        it will get written later.

        Args:
          link (Link):  Ourselves.
          connected (bool):  True if the device is connected.
        """
        assert self == link

        # If there are message waiting to send, emit the signal now that we
        # are connected.
        if connected and self._write_buf:
            self.signal_needs_write.emit(self, True)

    #-----------------------------------------------------------------------
    def __str__(self):
        return "Serial %s" % str(self._port)

    #-----------------------------------------------------------------------
