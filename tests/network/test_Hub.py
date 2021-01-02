#===========================================================================
#
# Tests for: insteont_mqtt/network/Hub.py
#
#===========================================================================
import time
import threading
import requests
import pytest
from pprint import pprint
from unittest import mock
from unittest.mock import call, patch
from requests.models import Response

import insteon_mqtt as IM
import insteon_mqtt.network.Hub as Hub
from insteon_mqtt.network.Hub import HubClient
import insteon_mqtt.message as Msg

@pytest.fixture
def test_hub():
    '''
    Returns a generically configured Hub for testing
    '''
    hub = Hub(ip="192.168.1.1", user='user', password='password')
    return hub

@pytest.fixture
def test_hubclient():
    '''
    Returns a generically configured Hub for testing
    '''
    # necessary to stop client from running
    with patch.object(threading, 'Thread'):
        return HubClient("192.168.1.1", 25105, "user", "password")

BUFFSTATUS = b"""
<response>
<BS>190006025C3B98C14B759823190002625058200519000602505058204B75982618000262221A9A1F2E02000000000000000000000000929606025C221A9A4B7598232E02027F0206027F0006027F0206027F00060006027F0206027F000602623B98C105A8</BS>
</response>"""

ORDEREDSTRING = "0006027F0206027F000602623B98C105190006025C3B98C14B759823190002625058200519000602505058204B75982618000262221A9A1F2E02000000000000000000000000929606025C221A9A4B7598232E02027F0206027F0006027F0206027F0006"

class Test_Hub:
    def test_config(self, test_hub):
        config = {"hub_port": 123, "hub_user": 'bob'}
        test_hub.load_config(config)
        assert test_hub._port == 123
        assert test_hub._user == 'bob'
        assert test_hub._password == 'password'
        assert test_hub._ip == '192.168.1.1'

    #-----------------------------------------------------------------------
    def test_write(self, test_hub):
        data = bytes([0x01])
        assert len(test_hub._write_buf) == 0
        test_hub.write(data)
        assert len(test_hub._write_buf) == 1
        for i in range(510):
            test_hub.write(data)
        assert len(test_hub._write_buf) == 500

    #-----------------------------------------------------------------------
    def test_poll(self, test_hub):
        assert test_hub.client is None
        with patch.object(threading, 'Thread'):
            test_hub.poll(time.time())
            assert test_hub.client is not None

    #-----------------------------------------------------------------------
    @pytest.mark.parametrize("read,expected,calls", [
        (None, None, 0),
        (bytes([0x01]), bytes([0x01]), 1)
    ])
    def test_read(self, test_hub, read, expected, calls):
        # necessary to stop client from running
        threading.Thread = mock.Mock()
        with patch.object(test_hub.signal_read, 'emit'):
            test_hub.poll(time.time())
            if read is not None:
                test_hub.client._read_queue.put(read)
            test_hub._read_from_hub()
            args_list = test_hub.signal_read.emit.call_args_list
            assert test_hub.signal_read.emit.call_count == calls
            if expected is not None:
                assert args_list[0][0][1] == expected

    #-----------------------------------------------------------------------
    @pytest.mark.parametrize("write,t,expected,buffer,calls", [
        (None, None, None, 0, 0),
        (bytes([0x00]), None, bytes([0x00]), 0, 1),
        (bytes([0x00]), time.time() + 10, None, 1, 0),
    ])
    def test_write(self, test_hub, write, t, expected, buffer, calls):
        # necessary to stop client from running
        threading.Thread = mock.Mock()
        with mock.patch.object(test_hub.signal_wrote, 'emit'):
            test_hub.poll(time.time())
            mock.patch.object(test_hub.client, 'write')
            if write is not None:
                test_hub.write(write, after_time=t)
            test_hub._write_to_hub(time.time())
            args_list = test_hub.signal_wrote.emit.call_args_list
            assert test_hub.signal_wrote.emit.call_count == calls
            assert len(test_hub._write_buf) == buffer
            if expected is not None:
                assert args_list[0][0][1] == expected

    #-----------------------------------------------------------------------
    def test_close(self, test_hub):
        # necessary to stop client from running
        threading.Thread = mock.Mock()
        with mock.patch.object(test_hub.signal_closing, 'emit'):
            # Starts the HubClient
            test_hub.poll(time.time())
            self._write_buf = [bytes([0x00])]
            test_hub.close()
            assert len(test_hub._write_buf) == 0
            assert test_hub.client._close == True
            assert test_hub.signal_closing.emit.call_count == 1

    #-----------------------------------------------------------------------
    def test_str(self, test_hub):
        assert "%s" % test_hub == "Hub 192.168.1.1"

class Test_HubClient:
    # I don't see a good way to test the _thread() function.  So I tried
    # to move all of the processing into seperate functions
    def test_get_buffer(self, test_hubclient):
        test_response = Response()
        test_response.status_code = 200
        test_response._content = BUFFSTATUS
        with patch.object(requests, 'get', return_value=test_response):
            response = test_hubclient._get_hub_buffer()
            assert response

    def test_get_buffer_timeout(self, test_hubclient):
        test_response = Response()
        test_response.status_code = 200
        test_response._content = BUFFSTATUS
        with patch.object(requests, 'get', side_effect=requests.exceptions.Timeout):
            response = test_hubclient._get_hub_buffer()
            assert test_hubclient.read_timeout_count == 1
            assert not response

    def test_get_buffer_repeated_timeout(self, test_hubclient):
        test_response = Response()
        test_response.status_code = 200
        test_response._content = BUFFSTATUS
        test_hubclient.read_timeout_count = 6
        with patch.object(requests, 'get', side_effect=requests.exceptions.Timeout):
            response = test_hubclient._get_hub_buffer()
            assert test_hubclient.read_timeout_count == 0

    def test_parse_buffer(self, test_hubclient):
        test_response = Response()
        test_response.status_code = 200
        test_response._content = BUFFSTATUS
        (bytestring, byte_end) = test_hubclient._parse_buffer(test_response)
        assert bytestring == ORDEREDSTRING
        assert byte_end == 168

    @pytest.mark.parametrize("bytestring,byte_end,expected,prev_str,prev_end", [
        (ORDEREDSTRING, 168, None, '', 0),
        (ORDEREDSTRING, 168, '0206027F0006', '7F0006027F', 156),
    ])
    def test_parse_bytes(self, test_hubclient, bytestring, byte_end, expected,
                         prev_str, prev_end):
        test_hubclient._prev_bytestring = prev_str
        test_hubclient._prev_byte_end = prev_end
        ret = test_hubclient._parse_bytes(bytestring, byte_end)
        assert ret == expected

    def test_perform_write(self, test_hubclient):
        with patch.object(requests, 'get'):
            test_hubclient.write(bytes([0x02,0x06]))
            test_hubclient._perform_write()
            args = requests.get.call_args
            assert args[0][0] == 'http://192.168.1.1:25105/3?0206=I=3'

    def test_perform_write_timeout(self, test_hubclient):
        with patch.object(requests, 'get', side_effect=requests.exceptions.Timeout):
            test_hubclient.write(bytes([0x02,0x06]))
            test_hubclient._perform_write()
            args = requests.get.call_args
            assert args[0][0] == 'http://192.168.1.1:25105/3?0206=I=3'
