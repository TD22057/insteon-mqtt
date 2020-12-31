#===========================================================================
#
# Tests for: insteont_mqtt/network/Serial.py
#
#===========================================================================
import time
import serial
import pytest
from pprint import pprint
from unittest import mock
from unittest.mock import call, patch

import insteon_mqtt as IM
import insteon_mqtt.network.Serial as IM_Serial
import insteon_mqtt.message as Msg

@pytest.fixture
def test_device():
    '''
    Returns a generically configured Serial obj for testing
    '''
    device = IM_Serial(port=None, baudrate=19200, parity=serial.PARITY_NONE,
                       reconnect_dt=10)
    device.client = FakeClient()
    return device

class FakeClient():
    def __init__(self):
        self.written = []
        self.write_max = None
        self.port = 123

    def write(self, data):
        if self.write_max is not None:
            self.written.append(data[:self.write_max])
            return self.write_max
        else:
            self.written.append(data)
            return len(data)

class Test_Serial():
    def test_write_to_link_empty(self, test_device):
        t = time.time()
        with patch.object(test_device.signal_needs_write, 'emit') as mock_emit:
            test_device.write_to_link(t)
            mock_emit.assert_called_once_with(test_device, False)

    def test_write_to_link_too_soon(self, test_device):
        t = time.time()
        test_device._write_buf.append((bytes(8), time.time() + 5))
        with patch.object(test_device.signal_needs_write, 'emit') as mock_emit:
            test_device.write_to_link(t)
            mock_emit.assert_not_called()

    def test_write_to_link_partial(self, test_device):
        test_device.client.write_max = 4
        msg_time = time.time()
        test_device._write_buf.append((bytes(8), msg_time))
        t = time.time()
        with patch.object(test_device.signal_needs_write, 'emit') as needs_emit:
            with patch.object(test_device.signal_wrote, 'emit') as wrote_emit:
                # Should only write the first 4 bytes and not emit
                test_device.write_to_link(t)
                wrote_emit.assert_not_called()
                needs_emit.assert_not_called()
                # Should still be 4 bytes in there
                assert len(test_device._write_buf[0][0]) == 4
                # After time should be the same
                assert test_device._write_buf[0][1] == msg_time
                # This should cause the rest of the data to be written
                test_device.write_to_link(t)
                needs_emit.assert_called_once_with(test_device, False)
                wrote_emit.assert_called_once_with(test_device, bytes(4))
                assert len(test_device._write_buf) == 0

    def test_write_to_link_exception(self, test_device, caplog):
        def write(data):
            raise Exception("Fake Serial", "Broken", "Test")
        test_device.client.write = write
        msg_time = time.time()
        test_device._write_buf.append((bytes(8), msg_time))
        t = time.time()
        test_device.write_to_link(t)
        assert "Serial write error" in caplog.text
