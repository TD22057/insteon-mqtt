#===========================================================================
#
# Tests for: insteont_mqtt/device/Remote.py
#
#===========================================================================
import pytest
# from pprint import pprint
from unittest import mock
from unittest.mock import call
import insteon_mqtt as IM
import insteon_mqtt.device.Remote as Remote
# import insteon_mqtt.message as Msg
import insteon_mqtt.util as util
import helpers as H

@pytest.fixture
def test_device4(tmpdir):
    '''
    Returns a generically configured iolinc for testing
    '''
    protocol = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    addr = IM.Address(0x01, 0x02, 0x03)
    device = Remote(protocol, modem, addr, "4button", 4)
    return device

@pytest.fixture
def test_device8(tmpdir):
    '''
    Returns a generically configured iolinc for testing
    '''
    protocol = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    addr = IM.Address(0x01, 0x02, 0x03)
    device = Remote(protocol, modem, addr, "8button", 8)
    return device

class Test_Base_Config():
    def test_pair4(self, test_device4):
        with mock.patch.object(IM.CommandSeq, 'add'):
            test_device4.pair()
            calls = [
                call(test_device4.refresh),
                call(test_device4.db_add_ctrl_of, 0x01, test_device4.modem.addr, 0x01,
                     refresh=False),
                call(test_device4.db_add_ctrl_of, 0x02, test_device4.modem.addr, 0x01,
                     refresh=False),
                call(test_device4.db_add_ctrl_of, 0x03, test_device4.modem.addr, 0x01,
                     refresh=False),
                call(test_device4.db_add_ctrl_of, 0x04, test_device4.modem.addr, 0x01,
                     refresh=False),
                     ]
            IM.CommandSeq.add.assert_has_calls(calls, any_order=True)
            assert IM.CommandSeq.add.call_count == 5

    def test_pair8(self, test_device8):
        with mock.patch.object(IM.CommandSeq, 'add'):
            test_device8.pair()
            calls = [
                call(test_device8.refresh),
                call(test_device8.db_add_ctrl_of, 0x01, test_device8.modem.addr, 0x01,
                     refresh=False),
                call(test_device8.db_add_ctrl_of, 0x02, test_device8.modem.addr, 0x01,
                     refresh=False),
                call(test_device8.db_add_ctrl_of, 0x03, test_device8.modem.addr, 0x01,
                     refresh=False),
                call(test_device8.db_add_ctrl_of, 0x04, test_device8.modem.addr, 0x01,
                     refresh=False),
                call(test_device8.db_add_ctrl_of, 0x05, test_device8.modem.addr, 0x01,
                     refresh=False),
                call(test_device8.db_add_ctrl_of, 0x06, test_device8.modem.addr, 0x01,
                     refresh=False),
                call(test_device8.db_add_ctrl_of, 0x07, test_device8.modem.addr, 0x01,
                     refresh=False),
                call(test_device8.db_add_ctrl_of, 0x08, test_device8.modem.addr, 0x01,
                     refresh=False),
                     ]
            IM.CommandSeq.add.assert_has_calls(calls, any_order=True)
            assert IM.CommandSeq.add.call_count == 9
