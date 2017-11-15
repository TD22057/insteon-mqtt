#===========================================================================
#
# Network and serial link management
#
#===========================================================================
import logging
import os
import serial
from .Link import Link
from .. import Signal

LOG = logging.getLogger(__name__)

class Serial (Link):
    """TODO: doc
    """
    read_buf_size = 4096

    #-----------------------------------------------------------------------
    def __init__(self, port=None, baudrate=19200, parity=serial.PARITY_NONE,
                 reconnect_dt=10):
        """TODO: doc
        """
        # Public signals to connect to.
        self.signal_read = Signal.Signal()   # (Serial, bytes)
        self.signal_wrote = Signal.Signal()  # (Serial, bytes)

        super().__init__()

        self._baudrate = baudrate
        self._parity = parity
        self._reconnect_dt = reconnect_dt
        self._write_buf = []
        self._fd = None

        # Create the serial client but don't open it yet.  We'll wait
        # for a connection call to do that.
        self.client = None if not port else self._open_client(port)

        self.signal_connected.connect(self._connected)

    #-----------------------------------------------------------------------
    def load_config(self, config):
        """TODO: doc
        """
        assert(self._fd is None)

        self._baudrate = config.get('baudrate', self._baudrate)
        self._parity = config.get('parity', self._parity)

        self._client = self._open_client(config['port'])

    #-----------------------------------------------------------------------
    def fileno(self):
        """TODO: doc
        """
        assert(self._fd)
        return self._fd

    #-----------------------------------------------------------------------
    def write(self, data):
        """TODO: doc
        """
        self._write_buf.append(data)
        self.signal_needs_write.emit(self, True)

    #-----------------------------------------------------------------------
    def retry_connect_dt(self):
        """TODO: doc
        """
        return self._reconnect_dt

    #-----------------------------------------------------------------------
    def connect(self):
        """TODO: doc
        """
        try:
            self.client.open()
            self._fd = self.client.fileno()

            LOG.info("Serial device opened %s", self.client.port)
            return True
        except:
            LOG.exception("Serial connection error to %s", self.client.port)
            return False

    #-----------------------------------------------------------------------
    def read_from_link(self):
        """TODO: doc
        """
        try:
            data = os.read(self._fd, self.read_buf_size)
            if data:
                #LOG.debug("Read %s bytes from serial %s: %s", len(data),
                #               self.client.port, data)

                self.signal_read.emit(self, data)
        except:
            LOG.exception("Serial read error from %s", self.client.port)

    #-----------------------------------------------------------------------
    def write_to_link(self):
        """TODO: doc
        """
        if not self._write_buf:
            self.signal_needs_write.emit(self, False)
            return

        data = self._write_buf[0]
        try:
            num = os.write(self._fd, data)

            LOG.debug("Wrote %s bytes to serial %s", num, self.client.port)

            if num == len(data):
                self._write_buf.pop(0)
                if not len(self._write_buf):
                    self.signal_needs_write.emit(self, False)

                self.signal_wrote.emit(self, data)

            elif num:
                self._write_buf[0] = data[num:]

        except:
            LOG.exception("Serial write error from %s", self.client.port)

    #-----------------------------------------------------------------------
    def close(self):
        """TODO: doc
        """
        if not self._fd:
            return

        LOG.info("Serial device closing %s", self.client.port)

        self.client.close()
        self._fd = None
        self._write_buf = []
        self.signal_closing.emit(self)

    #-----------------------------------------------------------------------
    def _open_client(self, port, connect=False):
        """TODO: doc
        """
        client = serial.serial_for_url(port, do_not_open=True, timeout=0,
                                       write_timeout=0)
        client.baudrate = self._baudrate
        client.parity = self._parity
        return client

    #-----------------------------------------------------------------------
    def _connected(self, link, connected):
        assert(self == link)

        # If there are message waiting to send, emit the signal now
        # that we are connected.
        if connected and self._write_buf:
            self.signal_needs_write.emit(self, True)
        
    #-----------------------------------------------------------------------
    def __str__(self):
        return "Serial %s" % self.client.port
    
    #-----------------------------------------------------------------------
