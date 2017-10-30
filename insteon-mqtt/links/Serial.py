#===========================================================================
#
# Network and serial link management
#
#===========================================================================
import logging
import os
import serial
from .Link import Link
from .. import sigslot


class Serial (Link):
    """TODO: doc
    """
    read_buf_size = 4096

    #-----------------------------------------------------------------------
    def __init__(self, port, baudrate=None, parity=serial.PARITY_NONE,
                 bytesize=serial.EIGHTBITS, reconnect_dt=10):
        """TODO: doc
        """
        # Public signals to connect to.
        self.signal_read = sigslot.Signal()   # (Serial, bytes)
        self.signal_wrote = sigslot.Signal()  # (Serial, bytes)

        super().__init__()

        self._reconnect_dt = reconnect_dt
        self._write_buf = []
        self._fd = None

        # Create the serial client but don't open it yet.  We'll wait
        # for a connection call to do that.
        self.client = serial.serial_for_url(port, do_not_open=True, timeout=0,
                                            write_timeout=0)
        self.client.baudrate = baudrate
        self.client.parity = parity
        self.client.bytesize = bytesize

        self.log = logging.getLogger(__name__)

    #-----------------------------------------------------------------------
    def fileno(self):
        return self._fd

    #-----------------------------------------------------------------------
    def write(self, data):
        self._write_buf.append(data)
        self.signal_needs_write.emit(True)

    #-----------------------------------------------------------------------
    def retry_connect_dt(self):
        return self._reconnect_dt

    #-----------------------------------------------------------------------
    def connect(self):
        try:
            self.client.open()
            self._fd = self.client.fileno()

            self.log.info("Serial device opened", self.client.port)
            return True
        except:
            self.log.exception("Serial connection error to", self.client.port)
            return False

    #-----------------------------------------------------------------------
    def read_from_link(self):
        try:
            data = os.read(self._fd, self.read_buf_size)
            if data:
                self.log.debug("Read", len(data), "bytes from serial",
                               self.client.port, data)

                self.signal_read.emit(self, data)
        except:
            self.log.exception("Serial read error from", self.client.port)

    #-----------------------------------------------------------------------
    def write_to_link(self):
        if not self._write_buf:
            self.signal_needs_write.emit(False)
            return

        data = self._write_buf[0]
        try:
            num = os.write(self._fd, data)

            self.log.debug("Wrote", num, "bytes to serial", self.client.port)

            if num == len(data):
                self._write_buf.pop(0)
                if not len(self._write_buf):
                    self.signal_needs_write.emit(False)

                self.signal_wrote.emit(self, data)

            elif num:
                self._write_buf[0] = data[num:]

        except:
            self.log.exception("Serial write error from", self.client.port)

    #-----------------------------------------------------------------------
    def close(self):
        self.log.info("Serial device closing", self.client.port)

        self.client.close()
        self._fd = None
        self.signal_closing.emit(self)

    #-----------------------------------------------------------------------
