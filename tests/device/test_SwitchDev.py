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
        (0x01,Msg.CmdType.ON, 0x00,{"is_on":True,"level":None,"mode":IM.on_off.Mode.NORMAL, "button":1, "reason":'device'}),
        (0x01,Msg.CmdType.OFF, 0x00, {"is_on":False,"level":None,"mode":IM.on_off.Mode.NORMAL, "button":1, "reason":'device'}),
        (0x01,Msg.CmdType.ON_FAST, 0x00,{"is_on":True,"level":None,"mode":IM.on_off.Mode.FAST, "button":1, "reason":'device'}),
        (0x01,Msg.CmdType.OFF_FAST, 0x00, {"is_on":False,"level":None,"mode":IM.on_off.Mode.FAST, "button":1, "reason":'device'}),
        (0x01,Msg.CmdType.LINK_CLEANUP_REPORT, 0x00, None),
    ])
    def test_handle_on_off(self, test_device, group, cmd1, cmd2, expected):
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, group)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, cmd1, cmd2)
            test_device.handle_broadcast(msg)
            if expected is not None:
                mocked.assert_called_once_with(test_device, **expected)
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
            calls = [call(test_device, button=1, manual=IM.on_off.Manual.DOWN,
                          reason='device'),
                     call(test_device, is_on=False, level=None,
                          mode=IM.on_off.Mode.MANUAL, button=1, reason='device')]
            mocked.assert_has_calls(calls)
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x01)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, Msg.CmdType.START_MANUAL_CHANGE, 0x01)
            test_device.handle_broadcast(msg)
            assert mocked.call_count == 2
            calls = [call(test_device, button=1, manual=IM.on_off.Manual.UP,
                          reason='device'),
                     call(test_device, is_on=True, button=1, level=None,
                          mode=IM.on_off.Mode.MANUAL, reason='device')]
            mocked.assert_has_calls(calls)

    def test_set_backlight(self, test_device):
        test_device.set_backlight(backlight=0)
        assert len(test_device.protocol.sent) == 1
        assert test_device.protocol.sent[0].msg.cmd1 == 0x20
        assert test_device.protocol.sent[0].msg.cmd2 == 0x08
        test_device.protocol.clear()

        def level_bytes(level):
            data = bytes([
                0x01,   # D1 must be group 0x01
                0x07,   # D2 set global led brightness
                level,  # D3 brightness level
                ] + [0x00] * 11)
            return data

        for params in ([1, 0x01], [255, 0xFF], [127, 127]):
            with mock.patch.object(IM.CommandSeq, 'add_msg'):
                test_device.set_backlight(backlight=params[0])
                args_list = IM.CommandSeq.add_msg.call_args_list
                assert IM.CommandSeq.add_msg.call_count == 2
                # Check the first call
                assert args_list[0][0][0].cmd1 == 0x20
                assert args_list[0][0][0].cmd2 == 0x09
                # Check the first call
                assert args_list[1][0][0].cmd1 == 0x2e
                assert args_list[1][0][0].data == level_bytes(params[1])


        with mock.patch.object(IM.CommandSeq, 'add_msg'):
            # test backlight off
            test_device.set_backlight(backlight=0)
            args_list = IM.CommandSeq.add_msg.call_args_list
            assert IM.CommandSeq.add_msg.call_count == 1
            # Check the first call
            assert args_list[0][0][0].cmd1 == 0x20
            assert args_list[0][0][0].cmd2 == 0x08

    def test_set_backlight_bad(self, test_device, caplog):
        def on_done(success, msg, data):
            assert not success
        test_device.set_backlight(backlight='badstring', on_done=on_done)
        assert 'Invalid backlight level' in caplog.text

    def test_set_flags(self, test_device):
        test_device.set_flags(None, backlight=0)
        assert len(test_device.protocol.sent) == 1
        assert test_device.protocol.sent[0].msg.cmd1 == 0x20
        assert test_device.protocol.sent[0].msg.cmd2 == 0x08

    def test_set_flags_bad(self, test_device, caplog):
        test_device.set_flags(None, bad=0)
        assert len(test_device.protocol.sent) == 0
        assert 'Unknown set flags input' in caplog.text
