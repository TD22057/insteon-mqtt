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
import insteon_mqtt.message as Msg
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

    @pytest.mark.parametrize("group_num,cmd1,cmd2,expected", [
        (0x01,Msg.CmdType.ON, 0x00,[True,IM.on_off.Mode.NORMAL]),
        (0x01,Msg.CmdType.OFF, 0x00, [False,IM.on_off.Mode.NORMAL]),
        (0x01,Msg.CmdType.ON_FAST, 0x00,[True,IM.on_off.Mode.FAST]),
        (0x01,Msg.CmdType.OFF_FAST, 0x00, [False,IM.on_off.Mode.FAST]),
        (0x01,Msg.CmdType.START_MANUAL_CHANGE, 0x00, [IM.on_off.Manual.DOWN]),
        (0x01,Msg.CmdType.START_MANUAL_CHANGE, 0x01, [IM.on_off.Manual.UP]),
        (0x01,Msg.CmdType.STOP_MANUAL_CHANGE, 0x00, [IM.on_off.Manual.STOP]),
        (0x01,Msg.CmdType.LINK_CLEANUP_REPORT, 0x00, None),
        (0x02,Msg.CmdType.ON, 0x00,[True,IM.on_off.Mode.NORMAL]),
        (0x03,Msg.CmdType.ON, 0x00,[True,IM.on_off.Mode.NORMAL]),
        (0x04,Msg.CmdType.ON, 0x00,[True,IM.on_off.Mode.NORMAL]),
        (0x05,Msg.CmdType.ON, 0x00,[True,IM.on_off.Mode.NORMAL]),
        (0x06,Msg.CmdType.ON, 0x00,[True,IM.on_off.Mode.NORMAL]),
        (0x07,Msg.CmdType.ON, 0x00,[True,IM.on_off.Mode.NORMAL]),
        (0x08,Msg.CmdType.ON, 0x00,[True,IM.on_off.Mode.NORMAL]),
    ])
    def test_handle_on_off(self, test_device8, group_num, cmd1, cmd2, expected):
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, group_num)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, cmd1, cmd2)
            test_device8.handle_broadcast(msg)
            if expected is not None:
                mocked.assert_called_once_with(test_device8, group_num, *expected)
            else:
                mocked.assert_not_called()
