#===========================================================================
#
# Tests for: insteont_mqtt/device/KeypadLinc.py
#
#===========================================================================
import pytest

from unittest import mock
from unittest.mock import call
import insteon_mqtt as IM
import insteon_mqtt.device.Base as Base
import insteon_mqtt.message as Msg
import insteon_mqtt.util as util
import helpers as H

@pytest.fixture
def test_device(tmpdir):
    '''
    Returns a generically configured keypadlinc for testing
    '''
    protocol = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    addr = IM.Address(0x01, 0x02, 0x03)
    device = IM.device.KeypadLinc(protocol, modem, addr, 'test_device')
    return device

def test_pair(test_device):
    with mock.patch.object(IM.CommandSeq, 'add'):
        test_device.pair()
        calls = [
            call(test_device.refresh),
            call(test_device.db_add_resp_of, 0x01, test_device.modem.addr, 0x01,
                 refresh=False),
            call(test_device.db_add_ctrl_of, 0x01, test_device.modem.addr, 0x01,
                 refresh=False),
            call(test_device.db_add_ctrl_of, 0x02, test_device.modem.addr, 0x02,
                 refresh=False),
            call(test_device.db_add_ctrl_of, 0x03, test_device.modem.addr, 0x03,
                 refresh=False),
            call(test_device.db_add_ctrl_of, 0x04, test_device.modem.addr, 0x04,
                 refresh=False),
            call(test_device.db_add_ctrl_of, 0x05, test_device.modem.addr, 0x05,
                 refresh=False),
            call(test_device.db_add_ctrl_of, 0x06, test_device.modem.addr, 0x06,
                 refresh=False),
            call(test_device.db_add_ctrl_of, 0x07, test_device.modem.addr, 0x07,
                 refresh=False),
            call(test_device.db_add_ctrl_of, 0x08, test_device.modem.addr, 0x08,
                 refresh=False)

        ]
        IM.CommandSeq.add.assert_has_calls(calls)
        assert IM.CommandSeq.add.call_count == 11

def test_refresh(test_device):
    with mock.patch.object(IM.CommandSeq, 'add_msg'):
        test_device.refresh()
        args_list = IM.CommandSeq.add_msg.call_args_list
        assert IM.CommandSeq.add_msg.call_count == 3
        # Check the first call
        assert args_list[0][0][0].cmd1 == 0x19
        assert args_list[0][0][0].cmd2 == 0x01
        # Check the second call
        assert args_list[1][0][0].cmd1 == 0x19
        assert args_list[1][0][0].cmd2 == 0x00
        # Check the third call
        assert args_list[2][0][0].cmd1 == 0x2e
        assert args_list[2][0][0].cmd2 == 0x00
        assert isinstance(args_list[2][0][0], Msg.OutExtended)

def test_link_data(test_device):
    # is_controller, group, data=None
    data = test_device.link_data(True, 0x01, data=None)
    assert data == bytes([0x03,0x00,0x01])
    data = test_device.link_data(True, 0x02, data=None)
    assert data == bytes([0x03,0x00,0x02])
    data = test_device.link_data(False, 0x02, data=None)
    assert data == bytes([0xff,0x1f,0x02])

def test_link_data_pretty(test_device):
    # is_controller, data
    data = test_device.link_data_to_pretty(True, data=[0x00,0x00,0x00])
    assert data == [{'data_1': 0}, {'data_2': 0}, {'group': 0}]
    data = test_device.link_data_to_pretty(True, data=[0x01,0x00,0x00])
    assert data == [{'data_1': 1}, {'data_2': 0}, {'group': 0}]
    data = test_device.link_data_to_pretty(False, data=[0xff,0x00,0x00])
    assert data == [{'on_level': 100.0}, {'ramp_rate': 540}, {'group': 0}]
    data = test_device.link_data_to_pretty(False, data=[0xff,0x1f,0x05])
    assert data == [{'on_level': 100.0}, {'ramp_rate': .1}, {'group': 5}]

def test_link_data_from_pretty(test_device):
    # link_data_from_pretty(self, is_controller, data):
    data = test_device.link_data_from_pretty(False, data={'on_level': 100.0,
                                                          'ramp_rate': .1,
                                                          'group': 5})
    assert data == [0xff, 0x1f, 0x05]
    data = test_device.link_data_from_pretty(False, data={'on_level': 100.0,
                                                          'ramp_rate': 540,
                                                          'group': 1})
    assert data == [0xff, 0x00, 0x01]
    data = test_device.link_data_from_pretty(True, data={'on_level': 100.0,
                                                         'ramp_rate': 540,
                                                         'group': 1})
    assert data == [None, None, 0x01]
    data = test_device.link_data_from_pretty(True, data={'data_1': 0x01,
                                                         'data_2': 0x02,
                                                         'data_3': 0x03})
    assert data == [0x01, 0x02, 0x03]
