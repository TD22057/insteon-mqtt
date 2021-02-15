#===========================================================================
#
# Tests for: insteont_mqtt/device/Leak.py
#
#===========================================================================
import pytest
# from pprint import pprint
from unittest import mock
from unittest.mock import call
import insteon_mqtt as IM
import insteon_mqtt.device.Leak as Leak
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
    device = Leak(protocol, modem, addr)
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
                call(test_device.db_add_ctrl_of, 0x04, test_device.modem.addr, 0x01,
                     refresh=False),
            ]
            IM.CommandSeq.add.assert_has_calls(calls)
            assert IM.CommandSeq.add.call_count == 4

    @pytest.mark.parametrize("group_num,cmd1,cmd2,expected,kwargs", [
        (0x01,Msg.CmdType.ON, 0x00, [], {'button': 1, 'is_on': True,
                                         'level': None,
                                         'mode': IM.on_off.Mode.NORMAL,
                                         'reason': 'device'}),
        (0x01,Msg.CmdType.OFF, 0x00, [], {'button': 1, 'is_on': False,
                                          'level': None,
                                          'mode': IM.on_off.Mode.NORMAL,
                                          'reason': 'device'}),
        (0x02,Msg.CmdType.ON, 0x00, [], {'button': 2, 'is_on': True,
                                         'level': None,
                                         'mode': IM.on_off.Mode.NORMAL,
                                         'reason': 'device'}),
        (0x02,Msg.CmdType.OFF, 0x00, [], {'button': 2, 'is_on': False,
                                          'level': None,
                                          'mode': IM.on_off.Mode.NORMAL,
                                          'reason': 'device'}),
        (0x04,Msg.CmdType.ON, 0x00, [True], {}),
    ])
    def test_handle_broadcast(self, test_device, group_num, cmd1, cmd2,
                              expected, kwargs):
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            self._is_wet = False
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, group_num)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, cmd1, cmd2)
            test_device.handle_broadcast(msg)
            mocked.assert_called_once_with(test_device, *expected,
                                           **kwargs)

    def test_handle_heartbeat(self, test_device):
        # tests updating the wet/dry state when heartbeat received
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            self._is_wet = False
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x04)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, Msg.CmdType.OFF, 0x00)
            test_device.handle_broadcast(msg)
            assert mocked.call_count == 2
            calls = [call(test_device, is_on=True, level=None,
                          mode=IM.on_off.Mode.NORMAL, button=2, reason=''),
                     call(test_device, True)]
            mocked.assert_has_calls(calls)

    def test_handle_refresh_not_wet(self, test_device):
        with mock.patch.object(test_device, '_set_state') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x04)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, Msg.CmdType.OFF, 0x00)
            test_device.handle_refresh(msg, group=2)
            mocked.assert_called_once_with(group=2, is_on=False,
                                           reason='refresh')

    def test_handle_refresh_wet(self, test_device):
        with mock.patch.object(test_device, '_set_state') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x04)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, Msg.CmdType.OFF, 0x11)
            test_device.handle_refresh(msg, group=2)
            mocked.assert_called_once_with(group=2, is_on=True,
                                           reason='refresh')
