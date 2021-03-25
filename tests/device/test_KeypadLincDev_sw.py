#===========================================================================
#
# Tests for: insteont_mqtt/device/KeypadLinc.py
#
#===========================================================================
import pytest

from unittest import mock
from unittest.mock import call
import insteon_mqtt as IM
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

class Test_KPL():
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
                call(test_device.db_add_ctrl_of, 0x04, test_device.modem.addr, 0x01,
                     refresh=False),
                call(test_device.db_add_ctrl_of, 0x05, test_device.modem.addr, 0x01,
                     refresh=False),
                call(test_device.db_add_ctrl_of, 0x06, test_device.modem.addr, 0x01,
                     refresh=False),
                call(test_device.db_add_ctrl_of, 0x07, test_device.modem.addr, 0x01,
                     refresh=False),
                call(test_device.db_add_ctrl_of, 0x08, test_device.modem.addr, 0x01,
                     refresh=False)
            ]
            IM.CommandSeq.add.assert_has_calls(calls)
            assert IM.CommandSeq.add.call_count == 9

    def test_refresh(self, test_device):
        with mock.patch.object(IM.CommandSeq, 'add_msg'):
            test_device.refresh()
            args_list = IM.CommandSeq.add_msg.call_args_list
            assert IM.CommandSeq.add_msg.call_count == 3
            # Check the first call
            assert args_list[0][0][0].cmd1 == 0x19
            assert args_list[0][0][0].cmd2 == 0x00
            # Check the second call
            assert args_list[1][0][0].cmd1 == 0x19
            assert args_list[1][0][0].cmd2 == 0x01
            # Check the third call
            assert args_list[2][0][0].cmd1 == 0x2e
            assert args_list[2][0][0].cmd2 == 0x00
            assert isinstance(args_list[2][0][0], Msg.OutExtended)

    def test_link_data(self, test_device):
        # is_controller, group, data=None
        data = test_device.link_data(True, 0x01, data=None)
        assert data == bytes([0x03, 0x00, 0x01])
        data = test_device.link_data(True, 0x02, data=None)
        assert data == bytes([0x03, 0x00, 0x02])
        data = test_device.link_data(False, 0x02, data=None)
        assert data == bytes([0xff, 0x00, 0x02])

    def test_link_data_pretty(self, test_device):
        # is_controller, data
        data = test_device.link_data_to_pretty(True, data=[0x00, 0x00, 0x00])
        assert data == [{'data_1': 0}, {'data_2': 0}, {'group': 0}]
        data = test_device.link_data_to_pretty(True, data=[0x01, 0x00, 0x00])
        assert data == [{'data_1': 1}, {'data_2': 0}, {'group': 0}]
        data = test_device.link_data_to_pretty(False, data=[0xff, 0x00, 0x00])
        assert data == [{'data_1': 255}, {'data_2': 0}, {'group': 0}]
        data = test_device.link_data_to_pretty(False, data=[0xff, 0x1f, 0x05])
        assert data == [{'data_1': 255}, {'data_2': 0x1F}, {'group': 5}]

    def test_link_data_from_pretty(self, test_device):
        # link_data_from_pretty(self, is_controller, data):
        data = test_device.link_data_from_pretty(False, data={'group': 5})
        assert data == [None, None, 0x05]
        data = test_device.link_data_from_pretty(False, data={'group': 1})
        assert data == [None, None, 0x01]
        data = test_device.link_data_from_pretty(True, data={'data_1': 0x01,
                                                             'data_2': 0x02,
                                                             'data_3': 0x03})
        assert data == [0x01, 0x02, 0x03]

    def test_set_load_attached(self, test_device):
        # set_load_attached(self, is_attached, on_done=None):
        test_device.set_load_attached(True)
        assert len(test_device.protocol.sent) == 1
        assert test_device.protocol.sent[0].msg.cmd1 == 0x20
        assert test_device.protocol.sent[0].msg.cmd2 == 0x1a

        test_device.protocol.clear()
        test_device.set_load_attached(False)
        assert len(test_device.protocol.sent) == 1
        assert test_device.protocol.sent[0].msg.cmd1 == 0x20
        assert test_device.protocol.sent[0].msg.cmd2 == 0x1b

    def test_set_button_led(self, test_device):
        # set_button_led(self, group, is_on, reason="", on_done=None)
        group = 0x09
        test_device.set_button_led(group, True)
        assert len(test_device.protocol.sent) == 0

        group = 0x00
        test_device.set_button_led(group, True)
        assert len(test_device.protocol.sent) == 0

        group = 0x01
        test_device.set_button_led(group, True)
        assert len(test_device.protocol.sent) == 0

        test_device._load_group = 1
        group = 0x01
        test_device.set_button_led(group, True)
        assert len(test_device.protocol.sent) == 0

        def group_bytes(group):
            data = bytes([
                0x01,
                0x09,
                group,
                ] + [0x00] * 11)
            return data
        for params in ([2, True, 0x02], [5, True, 0x10], [2, False, 0x00]):
            test_device.set_button_led(params[0], params[1])
            assert len(test_device.protocol.sent) == 1
            assert test_device.protocol.sent[0].msg.cmd1 == 0x2e
            assert test_device.protocol.sent[0].msg.data == group_bytes(params[2])
            test_device.protocol.clear()

    def test_set_backlight(self, test_device):
        # set_backlight(self, level, on_done=None)
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

    def test_set_flags(self, test_device):
        # set_flags(self, on_done, **kwargs)
        for params in ([{'backlight': 1}, test_device.set_backlight, 0x01],
                       [{'load_attached': 1}, test_device.set_load_attached, 0x01],
                       [{'follow_mask': 1, "group": 4},
                        test_device.set_led_follow_mask, 4],
                       [{'off_mask': 1, "group": 4},
                        test_device.set_led_off_mask, 4],
                       [{'signal_bits': 1}, test_device.set_signal_bits, 0x01],
                       [{'nontoggle_bits': 1}, test_device.set_nontoggle_bits, 0x01],
                      ):
            with mock.patch.object(IM.CommandSeq, 'add'):
                test_device.set_flags(None, **params[0])
                args_list = IM.CommandSeq.add.call_args_list
                assert IM.CommandSeq.add.call_count == 1
                assert args_list[0][0][0] == params[1]
                assert args_list[0][1] == params[0]

    def test_handle_refresh_state(self, test_device):
        # handle_refresh_state(self, msg, on_done):
        def on_done(success, *args):
            assert success == True
        msg = Msg.OutStandard(IM.Address(12,14,15),
                              Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False),
                              0x2e, 0x00, is_ack=True)
        test_device.handle_refresh_state(msg, on_done)


    @pytest.mark.parametrize("group_num,cmd1,cmd2,expected", [
        (0x01,Msg.CmdType.ON, 0x00,{"level":None,"mode":IM.on_off.Mode.NORMAL, "is_on": True, "reason":'device', "button":1}),
        (0x01,Msg.CmdType.OFF, 0x00, {"level":None,"mode":IM.on_off.Mode.NORMAL, "is_on": False, "reason":'device', "button":1}),
        (0x01,Msg.CmdType.ON_FAST, 0x00,{"level":None,"mode":IM.on_off.Mode.FAST, "is_on": True, "reason":'device', "button":1}),
        (0x01,Msg.CmdType.OFF_FAST, 0x00, {"level":None,"mode":IM.on_off.Mode.FAST, "is_on": False, "reason":'device', "button":1}),
        (0x01,Msg.CmdType.STOP_MANUAL_CHANGE, 0x00, {"manual":IM.on_off.Manual.STOP, "button":1, "reason":'device'}),
        (0x01,Msg.CmdType.LINK_CLEANUP_REPORT, 0x00, None),
        (0x02,Msg.CmdType.ON, 0x00,{"level":None,"mode":IM.on_off.Mode.NORMAL, "is_on": True, "reason":'device', "button":2}),
        (0x03,Msg.CmdType.ON, 0x00,{"level":None,"mode":IM.on_off.Mode.NORMAL, "is_on": True, "reason":'device', "button":3}),
        (0x04,Msg.CmdType.ON, 0x00,{"level":None,"mode":IM.on_off.Mode.NORMAL, "is_on": True, "reason":'device', "button":4}),
        (0x05,Msg.CmdType.ON, 0x00,{"level":None,"mode":IM.on_off.Mode.NORMAL, "is_on": True, "reason":'device', "button":5}),
        (0x06,Msg.CmdType.ON, 0x00,{"level":None,"mode":IM.on_off.Mode.NORMAL, "is_on": True, "reason":'device', "button":6}),
        (0x07,Msg.CmdType.ON, 0x00,{"level":None,"mode":IM.on_off.Mode.NORMAL, "is_on": True, "reason":'device', "button":7}),
        (0x08,Msg.CmdType.ON, 0x00,{"level":None,"mode":IM.on_off.Mode.NORMAL, "is_on": True, "reason":'device', "button":8}),
    ])
    def test_handle_on_off(self, test_device, group_num, cmd1, cmd2, expected):
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, group_num)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, cmd1, cmd2)
            test_device.handle_broadcast(msg)
            if expected is not None:
                mocked.assert_called_once_with(test_device, **expected)
            else:
                mocked.assert_not_called()

    @pytest.mark.parametrize("load_group,cmd1,cmd2,expected", [
        (0x01,Msg.CmdType.ON, 0xff,{"level":255,"mode":IM.on_off.Mode.NORMAL, "is_on": True, "reason":'command', "button":1}),
        (0x01,Msg.CmdType.OFF, 0x00, {"level":0,"mode":IM.on_off.Mode.NORMAL, "is_on": False, "reason":'command', "button":1}),
        (0x09,Msg.CmdType.ON, 0xff,{"level":255,"mode":IM.on_off.Mode.NORMAL, "is_on": True, "reason":'command', "button":9}),
        (0x09,Msg.CmdType.OFF, 0x00, {"level":0,"mode":IM.on_off.Mode.NORMAL, "is_on": False, "reason":'command', "button":9}),
    ])
    def test_on_off_ack(self, test_device, load_group, cmd1, cmd2, expected):
        def on_done(success, *args):
            pass
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            test_device._load_group = load_group
            flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
            from_addr = test_device.addr
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, from_addr, flags, cmd1, cmd2)
            test_device.handle_ack(msg, on_done)
            if expected is not None:
                mocked.assert_called_once_with(test_device, **expected)
            else:
                mocked.assert_not_called()

    def test_handle_manual_load(self, test_device):
        test_device._load_group = 1
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x01)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags,
                                  Msg.CmdType.START_MANUAL_CHANGE, 0x00)
            test_device.handle_broadcast(msg)
            calls = [
                call(test_device, manual=IM.on_off.Manual.DOWN, button=1,
                     reason='device'),
                call(test_device, button=1, level=0x00, is_on=None,
                     reason='device', mode=IM.on_off.Mode.MANUAL)
                ]
            assert mocked.call_count == 2
            mocked.assert_has_calls(calls, any_order=True)
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x01)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags,
                                  Msg.CmdType.START_MANUAL_CHANGE, 0x01)
            test_device.handle_broadcast(msg)
            calls = [
                call(test_device, manual=IM.on_off.Manual.UP, button=1,
                     reason='device'),
                call(test_device, button=1, is_on=None, level=0xFF,
                     reason='device', mode=IM.on_off.Mode.MANUAL)
                ]
            assert mocked.call_count == 2
            mocked.assert_has_calls(calls, any_order=True)

    def test_handle_manual_not_load(self, test_device):
        test_device._load_group = 1
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x02)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags,
                                  Msg.CmdType.START_MANUAL_CHANGE, 0x00)
            test_device.handle_broadcast(msg)
            calls = [
                call(test_device, manual=IM.on_off.Manual.DOWN, button=2,
                     reason='device')
                ]
            assert mocked.call_count == 1
            mocked.assert_has_calls(calls, any_order=True)
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x02)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags,
                                  Msg.CmdType.START_MANUAL_CHANGE, 0x01)
            test_device.handle_broadcast(msg)
            calls = [
                call(test_device, manual=IM.on_off.Manual.UP, button=2,
                     reason='device')
                ]
            assert mocked.call_count == 1
            mocked.assert_has_calls(calls, any_order=True)
