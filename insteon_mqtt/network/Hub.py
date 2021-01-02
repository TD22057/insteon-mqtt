#===========================================================================
#
# Insteon Hub class definition.
#
#===========================================================================
import xml.etree.ElementTree as ET
import time
import threading
import queue

import requests

from ..Signal import Signal
from .. import log
#from .Link import Link

LOG = log.get_logger(__name__)


class Hub():
    """A HTTP Network Interface for using the Insteon Hub as the Modem

    Works with the model 2245-222 Hub and likely others.  The Hubs only offer
    an http interface, at least as currently known.  Therefore in order to
    interface properly with the Hub, a HubClient is defined which runs in its
    own thread for directly interfacing with the Hub.

    This class is merely a bridge between what the PLM interface uses and the
    HubClient.
    """
    read_buf_size = 4096
    max_write_queue = 500

    def __init__(self, ip=None, port='25105', user=None, password=None):
        """Constructor.  Mostly just defines some attributes that are expected
        but un-needed.  The HubClient is started in poll().

        Args:
          ip: (str) the ip address of the Hub.
          port: (int) the port number of the Hub.
          user: (str) the Hub username
          password: (str) the Hub password
        """
        # Public signals to connect to for read/write notification.
        self.signal_read = Signal()   # (Hub, bytes)
        self.signal_wrote = Signal()  # (Hub, bytes)
        self.signal_connected = Signal()
        self.signal_closing = Signal()

        super().__init__()

        self._ip = ip
        self._port = port
        self._user = user
        self._password = password

        self.client = None

        # List of packets to write.  Each is a tuple of (bytes, time) where
        # the time is the time after which to do the write.
        self._write_buf = []

    #-----------------------------------------------------------------------
    def load_config(self, config):
        """Load a configuration dictionary.

        Configuration inputs will override any set in the constructor.

        The input configuration dictionary may contain:
        - hub_ip (str):  The Hub ip address (mandatory)
        - hub_user (str):  The Hub username (mandatory)
        - hub_password (str):  The Hub password (mandatory)
        - hub_port (int): The Hub port (optional)

        Args:
          config (dict):  Configuration data to load.
        """
        self._port = config.get('hub_port', self._port)
        self._ip = config.get('hub_ip', self._ip)
        self._user = config.get('hub_user', self._user)
        self._password = config.get('hub_password', self._password)
        # Go ahead and crash now, otherwise we will crash in a more confusing
        # place
        assert self._ip is not None
        assert self._user is not None
        assert self._password is not None

    #-----------------------------------------------------------------------
    def write(self, data, after_time=None):
        """Schedule data for writing to the serial device.

        This pushes the data into a queue for writing to the Hub device.
        The data is pushed to the HubClient in poll() and written during
        the next HubClient loop.

        Args:
          after_time (float):  Time in seconds past epoch after which to write
                     the packet.  If None, the message will be sent whenever
                     it can.
        """
        # Default after time is 0 which will always write.
        after_time = after_time if after_time is not None else 0

        # Save the input data to the write queue.
        self._write_buf.append((data, after_time))

        # if we have exceed the max queue size, pop the oldest packet off.
        # This way if the link goes down for a long time, we don't just build
        # up a infinite number of packets to write.
        if (Hub.max_write_queue and
                len(self._write_buf) > Hub.max_write_queue):
            self._write_buf.pop(0)

    #-----------------------------------------------------------------------
    def poll(self, t):
        """Periodic poll callback.

        Pushes the messages to write to the HubClient and checks for incomming
        messages from the HubClient.

        Will spawn the HubClient on the first call.

        Args:
           t (float):  Current Unix clock time tag.
        """
        if self.client is None:
            # To allow config to load, this is run on the first loop
            self.client = HubClient(self._ip, self._port, self._user,
                                    self._password)
        self._read_from_hub()
        self._write_to_hub(t)

    #-----------------------------------------------------------------------
    def _read_from_hub(self):
        """Read data from the hub

        This is called by the poll call on every loop.
        """
        if self.client.has_read_data():
            data = self.client.read()
            self.signal_read.emit(self, data)

    #-----------------------------------------------------------------------
    def _write_to_hub(self, t):
        """Write data to the hub

        This is called by the poll call on every loop.

        Args:
           t (float:  The current time (time.time).
        """
        if not self._write_buf:
            return

        # Get the next data packet to write from the write queue and see if
        # enough time has elapsed to write the message.
        data, after_time = self._write_buf[0]
        if t < after_time:
            return

        self.client.write(data)
        LOG.debug("Wrote to hub %s", self._ip)
        self._write_buf.pop(0)

        # Signal that the packet was written.
        self.signal_wrote.emit(self, data)

    #-----------------------------------------------------------------------
    def close(self):
        """Close the link.

        The link will call self.signal_closing.emit() after closing.
        """
        LOG.info("Hib device closing %s", self._ip)

        self.client.close()
        self._write_buf = []
        self.signal_closing.emit(self)

    #-----------------------------------------------------------------------
    def __str__(self):
        return "Hub %s" % str(self._ip)

    #-----------------------------------------------------------------------


class HubClient:
    def __init__(self, ip, port, user, password):
        """Constructor.

        Args:
          ip: (str) the ip address of the Hub.
          port: (int) the port number of the Hub.
          user: (str) the Hub username
          password: (str) the Hub password
        """
        self.ip = ip
        self.port = port
        self.user = user
        self.password = password
        # Flag for close signal
        self._close = False
        self._read_queue = queue.Queue()
        self._write_queue = queue.Queue()
        self.read_timeout_count = 0
        self._prev_bytestring = ''
        self._prev_byte_end = -1
        # My current hub uses a 200 character buffer, not sure if any other
        # lengths could or do exists, this would have to adjusted if they
        # do.
        self.buff_length = 200

        # This is the length of chracters that must be matched for this to be
        # deemed a valid message.  10 characters which results in 5 bytes, is
        # only 5% of the buffer.  Too small a number, and we could pass
        # incorrect messages if the buffer "overflows" before we read it.
        # To large a number and more "overflows" will occur as we have less
        # usable buffer length
        self.verify_length = 10

        # Fire up the Client Thread
        threading.Thread(target=self._thread).start()

    def close(self):
        '''Terminates the HubClient thread on the next loop.
        '''
        self._close = True

    def has_read_data(self):
        '''Returns True if there is incoming data to be read.
        '''
        if self._read_queue.empty():
            return False
        else:
            return True

    def read(self):
        '''Returns the contents of the read queue as a bytearray.
        '''
        ret = bytearray()
        while not self._read_queue.empty():
            ret.extend(self._read_queue.get())
        return ret

    def write(self, bytes):
        '''Puts the bytes into the write queue.

        Args:
          bytes (bytearray): This should represent a complete message.
        '''
        self._write_queue.put(bytes)

    def _thread(self):
        '''This runs in its own thread.  It constantly loops until the main
        thread is terminated or self.close() is called.
        '''
        while threading.main_thread().is_alive() and not self._close:
            start_time = time.time()

            # Read First, get Buffer Contents
            response = self._get_hub_buffer()
            if not response:
                # Error reading the buffer pause slightly before looping
                time.sleep(.1)
                continue

            # reset on successful read
            self.read_timeout_count = 0

            (bytestring, byte_end) = self._parse_buffer(response)

            new_string = self._parse_bytes(bytestring, byte_end)
            if new_string is not None:
                self._read_queue.put((bytes.fromhex(new_string)))

            # Now write
            self._perform_write()

            # Only hammering at hub server twice per second.  Seems to result
            # in the PLM ACK and device message arriving together, but no more
            # than that. Could consider slowing down, but waiting too long
            # could cause the buffer to overflow and would slow down our
            # responses.  Would also need to increase the hub ack_time
            # accordingly too.  I have done up to 3 requests per second with
            # good results.
            sleep_time = (start_time + .5) - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            elif sleep_time < -2:
                seconds = str(round(abs(sleep_time), 2))
                LOG.warning('Hub %s loop took %s to complete', self.ip,
                            seconds)

    def _get_hub_buffer(self):
        '''
        Performs the HTTP call to get the read buffer.
        '''
        try:
            response = requests.get('http://%s:%s/buffstatus.xml' %
                                    (self.ip, self.port),
                                    auth=requests.auth.HTTPBasicAuth(
                                        self.user,
                                        self.password),
                                    timeout=5)
        except requests.exceptions.Timeout:
            # Warn for a bit, this can happen if the hub is overloaded
            LOG.warning('Timeout reading from Hub %s', self.ip)
            self.read_timeout_count += 1
            if self.read_timeout_count > 6:
                # Error if failed for 30 seconds
                LOG.error('Unable to read from Hub %s for 30 seconds',
                          self.ip)
                self.read_timeout_count = 0
            return False
        return response

    def _parse_buffer(self, response):
        '''
        The hub uses a ring buffer passed as a hexadecimal string with the
        final byte describing the position of the end of the buffer.  This
        function slices the buffer at the end point and stiches it back
        together in the proper order.
        '''
        # This could be done without ElementTree, I wonder if it is overkill
        root = ET.fromstring(response.text)
        # This seems overly complex, can this be directly referenced?
        # for response in root:
        #     if response.tag == 'BS':
        #         bytestring = response.text
        #         break
        bytestring = root.find('BS').text

        # Place buffer in sequential order
        # The last byte of the bytestring tells us where the buffer ends
        byte_end = int(bytestring[-2:], 16)
        # Get bytes after buffer end and put them first, then add bytes
        # that come before the buffer end
        bytestring = bytestring[byte_end:-2] + bytestring[:byte_end]

        return (bytestring, byte_end)

    def _parse_bytes(self, bytestring, byte_end):
        '''
        This parses out the new bytes out of the buffer.  It also verifies that
        the buffer has not overflowed
        '''
        ret = None
        if self._prev_bytestring != '' and self._prev_byte_end >= 0:
            new_length = byte_end - self._prev_byte_end
            # fix length if we have looped around on the ring
            if new_length < 0:
                new_length = (self.buff_length + new_length)

            verify_start = self.buff_length - self.verify_length - new_length
            verify_end = self.buff_length - new_length
            verify_bytestring = bytestring[verify_start : verify_end]
            if new_length > 0:
                if self._prev_bytestring == verify_bytestring:
                    ret = bytestring[-new_length:]
                else:
                    LOG.error('Read buff overflow Hub %s, prev %s, verify %s',
                              self.ip, self._prev_bytestring,
                              verify_bytestring)

        self._prev_bytestring = bytestring[-self.verify_length:]
        self._prev_byte_end = byte_end
        return ret

    def _perform_write(self):
        ''' Writes to the hub if there are messages Waiting
        '''
        if not self._write_queue.empty():
            command = self._write_queue.get()
            cmd_str = command.hex()
            url = 'http://%s:%s/3?%s=I=3' % (self.ip, self.port, cmd_str)
            try:
                requests.get(url,
                             auth=requests.auth.HTTPBasicAuth(self.user,
                                                              self.password),
                             timeout=3)
            except requests.exceptions.Timeout:
                # Since there are retries built in above this, we don't resend
                # here on the chance that the message did get through
                LOG.error('Unable to write to Hub %s', self.ip)
            # When we write to the Hub, it empties and resets the read buffer
            if self.verify_length > 0:
                empty = '0'
                self._prev_bytestring = empty * self.verify_length
            else:
                self._prev_bytestring = ''
            self._prev_byte_end = 0
