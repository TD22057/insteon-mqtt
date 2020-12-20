#===========================================================================
#
# Tests for: insteont_mqtt/device/Switch.py
#
#===========================================================================
import pytest
# from pprint import pprint
from unittest import mock
from unittest.mock import call
import insteon_mqtt as IM
import insteon_mqtt.device.Switch as Switch
import insteon_mqtt.message as Msg
import insteon_mqtt.util as util
import helpers as H

@pytest.fixture
def test_device(tmpdir):
    '''
    Returns a generically configured iolinc for testing
    '''
    protocol = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    addr = IM.Address(0x01, 0x02, 0x03)
    device = Switch(protocol, modem, addr)
    return device


class Test_Base_Config():
    def test_pair(self, test_device):
        with mock.patch.object(IM.CommandSeq, 'add'):
            test_device.pair()
            calls = [
                call(test_device.refresh),
                call(test_device.db_add_ctrl_of, 0x01, test_device.modem.addr, 0x01,
                     refresh=False),
            ]
            IM.CommandSeq.add.assert_has_calls(calls)
            assert IM.CommandSeq.add.call_count == 2

    @pytest.mark.parametrize("group,cmd1,cmd2,expected", [
        (0x01,Msg.CmdType.ON, 0x00,[True,IM.on_off.Mode.NORMAL, 'device']),
        (0x01,Msg.CmdType.OFF, 0x00, [False,IM.on_off.Mode.NORMAL, 'device']),
        (0x01,Msg.CmdType.ON_FAST, 0x00,[True,IM.on_off.Mode.FAST, 'device']),
        (0x01,Msg.CmdType.OFF_FAST, 0x00, [False,IM.on_off.Mode.FAST, 'device']),
        (0x01,Msg.CmdType.LINK_CLEANUP_REPORT, 0x00, None),
        (0x01,Msg.CmdType.STOP_MANUAL_CHANGE, 0x00, [IM.on_off.Manual.STOP]),
    ])
    def test_handle_on_off(self, test_device, group, cmd1, cmd2, expected):
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, group)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, cmd1, cmd2)
            test_device.handle_broadcast(msg)
            if expected is not None:
                mocked.assert_called_once_with(test_device, *expected)
            else:
                mocked.assert_not_called()

    def test_handle_on_off_manual(self, test_device):
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x01)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, Msg.CmdType.START_MANUAL_CHANGE, 0x00)
            test_device.handle_broadcast(msg)
            assert mocked.call_count == 2
            calls = [call(test_device, IM.on_off.Manual.DOWN),
                     call(test_device, False, IM.on_off.Mode.MANUAL, 'device')]
            mocked.assert_has_calls(calls)
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x01)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, Msg.CmdType.START_MANUAL_CHANGE, 0x01)
            test_device.handle_broadcast(msg)
            assert mocked.call_count == 2
            calls = [call(test_device, IM.on_off.Manual.UP),
                     call(test_device, True, IM.on_off.Mode.MANUAL, 'device')]
            mocked.assert_has_calls(calls)
