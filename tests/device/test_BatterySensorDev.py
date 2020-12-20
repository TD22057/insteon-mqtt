#===========================================================================
#
# Tests for: insteont_mqtt/device/BatterySensor.py
#
#===========================================================================
import pytest
# from pprint import pprint
from unittest import mock
from unittest.mock import call
import insteon_mqtt as IM
import insteon_mqtt.device.BatterySensor as BatterySensor
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
    device = BatterySensor(protocol, modem, addr)
    return device


class Test_Base_Config():
    def test_pair(self, test_device):
        with mock.patch.object(IM.CommandSeq, 'add'):
            test_device.pair()
            calls = [
                call(test_device.refresh),
                call(test_device.db_add_ctrl_of, 0x01, test_device.modem.addr, 0x01,
                     refresh=False),
                call(test_device.db_add_ctrl_of, 0x03, test_device.modem.addr, 0x01,
                     refresh=False),
                call(test_device.db_add_ctrl_of, 0x04, test_device.modem.addr, 0x01,
                     refresh=False),
            ]
            IM.CommandSeq.add.assert_has_calls(calls)
            assert IM.CommandSeq.add.call_count == 4

    @pytest.mark.parametrize("cmd_type,expected", [
        (Msg.CmdType.ON, True),
        (Msg.CmdType.OFF, False),
        (Msg.CmdType.LINK_CLEANUP_REPORT, None),
    ])
    def test_broadcast_1(self, test_device, cmd_type, expected):
        with mock.patch.object(BatterySensor, '_set_is_on') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x01)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, cmd_type, 0x00)
            test_device.handle_broadcast(msg)
            if expected is not None:
                mocked.assert_called_once_with(expected)
            else:
                mocked.assert_not_called()

    @pytest.mark.parametrize("cmd_type,expected", [
        (Msg.CmdType.ON, True),
        (Msg.CmdType.OFF, False),
        (Msg.CmdType.LINK_CLEANUP_REPORT, None),
    ])
    def test_broadcast_3(self, test_device, cmd_type, expected):
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x03)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, cmd_type, 0x00)
            test_device.handle_broadcast(msg)
            if expected is not None:
                mocked.assert_called_once_with(test_device, expected)
            else:
                mocked.assert_not_called()

    @pytest.mark.parametrize("cmd_type,expected", [
        (Msg.CmdType.ON, True),
        (Msg.CmdType.OFF, True),
        (Msg.CmdType.LINK_CLEANUP_REPORT, None),
    ])
    def test_broadcast_4(self, test_device, cmd_type, expected):
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x04)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, cmd_type, 0x00)
            test_device.handle_broadcast(msg)
            if expected is not None:
                mocked.assert_called_once_with(test_device, expected)
            else:
                mocked.assert_not_called()
