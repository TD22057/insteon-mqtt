#===========================================================================
#
# Tests for: insteont_mqtt/device/SmokeBridge.py
#
#===========================================================================
import pytest
# from pprint import pprint
from unittest import mock
from unittest.mock import call
import insteon_mqtt as IM
import insteon_mqtt.device.SmokeBridge as SmokeBridge
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
    device = SmokeBridge(protocol, modem, addr)
    return device

class Test_Base_Config():
    def test_pair(self, test_device):
        with mock.patch.object(IM.CommandSeq, 'add'):
            test_device.pair()
            calls = [
                call(test_device.refresh),
                call(test_device.db_add_ctrl_of, 0x01, test_device.modem.addr, 0x01,
                     refresh=False),
                call(test_device.db_add_ctrl_of, 0x02, test_device.modem.addr, 0x01,
                     refresh=False),
                call(test_device.db_add_ctrl_of, 0x03, test_device.modem.addr, 0x01,
                     refresh=False),
                call(test_device.db_add_ctrl_of, 0x05, test_device.modem.addr, 0x01,
                     refresh=False),
                call(test_device.db_add_ctrl_of, 0x06, test_device.modem.addr, 0x01,
                     refresh=False),
                call(test_device.db_add_ctrl_of, 0x07, test_device.modem.addr, 0x01,
                     refresh=False),
                call(test_device.db_add_ctrl_of, 0x0A, test_device.modem.addr, 0x01,
                     refresh=False),
                     ]
            IM.CommandSeq.add.assert_has_calls(calls, any_order=True)
            assert IM.CommandSeq.add.call_count == 8

    @pytest.mark.parametrize("group_num,cmd1,cmd2,expected", [ #1235670a
        (0x01,Msg.CmdType.ON, 0x00,[True]),
        (0x01,Msg.CmdType.OFF, 0x00, None),
        (0x01,Msg.CmdType.LINK_CLEANUP_REPORT, 0x00, None),
        (0x02,Msg.CmdType.ON, 0x00,[True]),
        (0x03,Msg.CmdType.ON, 0x00,[True]),
        (0x06,Msg.CmdType.ON, 0x00,[True]),
        (0x07,Msg.CmdType.ON, 0x00,[True]),
        (0x0A,Msg.CmdType.ON, 0x00,[True]),
    ])
    def test_handle_broadcast(self, test_device, group_num, cmd1, cmd2, expected):
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            self._is_wet = False
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, group_num)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, cmd1, cmd2)
            test_device.handle_broadcast(msg)
            if expected is not None:
                mocked.assert_called_once_with(test_device, group_num, *expected)
            else:
                mocked.assert_not_called()

    def test_handle_broadcast_clear(self, test_device):
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            self._is_wet = False
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x05)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, Msg.CmdType.ON, 0x00)
            test_device.handle_broadcast(msg)
            assert mocked.call_count == 6
            calls = []
            for type in test_device.Type:
                if type == test_device.Type.CLEAR:
                    continue
                calls.append(call(test_device, type, False))
            mocked.assert_has_calls(calls)
