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
            assert args_list[0][0][0].cmd2 == 0x01
            # Check the second call
            assert args_list[1][0][0].cmd1 == 0x19
            assert args_list[1][0][0].cmd2 == 0x00
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
        assert data == bytes([0xff, 0x1f, 0x02])

    def test_link_data_pretty(self, test_device):
        # is_controller, data
        data = test_device.link_data_to_pretty(True, data=[0x00, 0x00, 0x00])
        assert data == [{'data_1': 0}, {'data_2': 0}, {'group': 0}]
        data = test_device.link_data_to_pretty(True, data=[0x01, 0x00, 0x00])
        assert data == [{'data_1': 1}, {'data_2': 0}, {'group': 0}]
        data = test_device.link_data_to_pretty(False, data=[0xff, 0x00, 0x00])
        assert data == [{'on_level': 100.0}, {'ramp_rate': 540}, {'group': 0}]
        data = test_device.link_data_to_pretty(False, data=[0xff, 0x1f, 0x05])
        assert data == [{'on_level': 100.0}, {'ramp_rate': .1}, {'group': 5}]

    def test_link_data_from_pretty(self, test_device):
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

    def test_increment_up(self, test_device):
        # increment_up(self, reason="", on_done=None)
        # Switch shouldn't do anything
        test_device.is_dimmer = False
        test_device.increment_up()
        assert len(test_device.protocol.sent) == 0

        # dimmer
        test_device.is_dimmer = True
        test_device.increment_up()
        assert len(test_device.protocol.sent) == 1
        assert test_device.protocol.sent[0].msg.cmd1 == 0x15

    def test_increment_down(self, test_device):
        # increment_up(self, reason="", on_done=None)
        # Switch shouldn't do anything
        test_device.is_dimmer = False
        test_device.increment_down()
        assert len(test_device.protocol.sent) == 0

        # dimmer
        test_device.is_dimmer = True
        test_device.increment_down()
        assert len(test_device.protocol.sent) == 1
        assert test_device.protocol.sent[0].msg.cmd1 == 0x16

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
        test_device.set_backlight(0)
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

        for params in ([1, 0x11], [255, 0x7F], [127, 127]):
            with mock.patch.object(IM.CommandSeq, 'add_msg'):
                test_device.set_backlight(params[0])
                args_list = IM.CommandSeq.add_msg.call_args_list
                assert IM.CommandSeq.add_msg.call_count == 1
                # Check the first call
                assert args_list[0][0][0].cmd1 == 0x2e
                assert args_list[0][0][0].data == level_bytes(params[1])

        with mock.patch.object(IM.CommandSeq, 'add'):
            # test backlight off
            test_device._backlight = False
            test_device.set_backlight(1)
            args_list = IM.CommandSeq.add.call_args_list
            assert IM.CommandSeq.add.call_count == 1
            # Check the first call
            assert args_list[0][0][1]

    def test_set_ramp_rate(self, test_device):
        # set_ramp_rate(self, rate, on_done=None)
        # Test switch
        test_device.is_dimmer = False
        test_device.set_ramp_rate(5)
        assert len(test_device.protocol.sent) == 0

        # Test dimmer
        test_device.is_dimmer = True
        def level_bytes(level):
            data = bytes([
                0x01,   # D1 must be group 0x01
                0x05,   # D2 set global led brightness
                level,  # D3 brightness level
                ] + [0x00] * 11)
            return data
        for params in ([.1, 0x1f], [540, 0x00], [600, 0x00], [.0001, 0x1c]):
            test_device.set_ramp_rate(params[0])
            assert len(test_device.protocol.sent) == 1
            assert test_device.protocol.sent[0].msg.cmd1 == 0x2e
            assert test_device.protocol.sent[0].msg.data == level_bytes(params[1])
            test_device.protocol.clear()

    def test_set_on_level(self, test_device):
        # set_on_level(self, level, on_done=None)
        # Test switch
        test_device.is_dimmer = False
        test_device.set_on_level(5)
        assert len(test_device.protocol.sent) == 0

        # Test dimmer
        test_device.is_dimmer = True
        assert(test_device.get_on_level() == 255)

        def level_bytes(level):
            data = bytes([
                0x01,
                0x06,
                level,
                ] + [0x00] * 11)
            return data
        for params in ([1, 0x01], [127, 127], [255, 0xFF]):
            test_device.set_on_level(params[0])
            assert len(test_device.protocol.sent) == 1
            assert test_device.protocol.sent[0].msg.cmd1 == 0x2e
            assert (test_device.protocol.sent[0].msg.data ==
                    level_bytes(params[1]))
            test_device.protocol.clear()

        test_device.set_on_level(64)

        # Fake having completed the set_on_level(64) request
        flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
        ack = IM.message.InpStandard(test_device.addr.hex,
                                     test_device.modem.addr.hex,
                                     flags, 0x2e, 0x00)
        test_device.handle_on_level(ack, IM.util.make_callback(None), 64)
        assert(test_device.get_on_level() == 64)
        test_device.protocol.clear()

        # Try multiple button presses in a row; confirm that level goes to
        # default on-level then to full brightness, as expected.
        # Fast-on should always go to full brightness.
        params = [
            (Msg.CmdType.ON, 0x00, [64, IM.on_off.Mode.NORMAL, 'device']),
            (Msg.CmdType.ON, 0x00, [255, IM.on_off.Mode.NORMAL, 'device']),
            (Msg.CmdType.ON, 0x00, [64, IM.on_off.Mode.NORMAL, 'device']),
            (Msg.CmdType.OFF, 0x00, [0, IM.on_off.Mode.NORMAL, 'device']),
            (Msg.CmdType.ON_FAST, 0x00, [255, IM.on_off.Mode.FAST, 'device']),
            (Msg.CmdType.ON_FAST, 0x00, [255, IM.on_off.Mode.FAST, 'device']),
            (Msg.CmdType.OFF_FAST, 0x00, [0, IM.on_off.Mode.FAST, 'device']),
            (Msg.CmdType.ON_INSTANT, 0x00,
                [64, IM.on_off.Mode.INSTANT, 'device']),
            (Msg.CmdType.ON_INSTANT, 0x00,
                [255, IM.on_off.Mode.INSTANT, 'device']),
            (Msg.CmdType.ON_INSTANT, 0x00,
                [64, IM.on_off.Mode.INSTANT, 'device'])]
        for cmd1, cmd2, expected in params:
            with mock.patch.object(IM.Signal, 'emit') as mocked:
                print("Trying:", "[%x, %x]" % (cmd1, cmd2))
                flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
                group_num = 0x01
                group = IM.Address(0x00, 0x00, group_num)
                addr = IM.Address(0x01, 0x02, 0x03)
                msg = Msg.InpStandard(addr, group, flags, cmd1, cmd2)
                test_device.handle_broadcast(msg)
                if expected is not None:
                    mocked.assert_called_once_with(test_device, group_num,
                                                   *expected)
                else:
                    mocked.assert_not_called()

    def test_set_flags(self, test_device):
        # set_flags(self, on_done, **kwargs)
        for params in ([{'backlight': 1}, test_device.set_backlight, 0x01],
                       [{'load_attached': 1}, test_device.set_load_attached, 0x01],
                       [{'on_level': 127}, test_device.set_on_level, 0x7F],
                       [{'ramp_rate': .1}, test_device.set_ramp_rate, .1],
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
                assert args_list[0][0][1] == params[2]

    def test_handle_refresh_state(self, test_device):
        # handle_refresh_state(self, msg, on_done):
        def on_done(success, *args):
            assert success == True
        msg = Msg.OutStandard(IM.Address(12,14,15),
                              Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False),
                              0x2e, 0x00, is_ack=True)
        test_device.handle_refresh_state(msg, on_done)


    @pytest.mark.parametrize("group_num,cmd1,cmd2,expected", [
        (0x01,Msg.CmdType.ON, 0x00,[255,IM.on_off.Mode.NORMAL, 'device']),
        (0x01,Msg.CmdType.OFF, 0x00, [0,IM.on_off.Mode.NORMAL, 'device']),
        (0x01,Msg.CmdType.ON_FAST, 0x00,[255,IM.on_off.Mode.FAST, 'device']),
        (0x01,Msg.CmdType.OFF_FAST, 0x00, [0,IM.on_off.Mode.FAST, 'device']),
        (0x01,Msg.CmdType.START_MANUAL_CHANGE, 0x00, [IM.on_off.Manual.DOWN, 'device']),
        (0x01,Msg.CmdType.START_MANUAL_CHANGE, 0x01, [IM.on_off.Manual.UP, 'device']),
        (0x01,Msg.CmdType.STOP_MANUAL_CHANGE, 0x00, [IM.on_off.Manual.STOP, 'device']),
        (0x01,Msg.CmdType.LINK_CLEANUP_REPORT, 0x00, None),
        (0x02,Msg.CmdType.ON, 0x00,[255,IM.on_off.Mode.NORMAL, 'device']),
        (0x03,Msg.CmdType.ON, 0x00,[255,IM.on_off.Mode.NORMAL, 'device']),
        (0x04,Msg.CmdType.ON, 0x00,[255,IM.on_off.Mode.NORMAL, 'device']),
        (0x05,Msg.CmdType.ON, 0x00,[255,IM.on_off.Mode.NORMAL, 'device']),
        (0x06,Msg.CmdType.ON, 0x00,[255,IM.on_off.Mode.NORMAL, 'device']),
        (0x07,Msg.CmdType.ON, 0x00,[255,IM.on_off.Mode.NORMAL, 'device']),
        (0x08,Msg.CmdType.ON, 0x00,[255,IM.on_off.Mode.NORMAL, 'device']),
    ])
    def test_handle_on_off(self, test_device, group_num, cmd1, cmd2, expected):
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, group_num)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, cmd1, cmd2)
            test_device.handle_broadcast(msg)
            if expected is not None:
                mocked.assert_called_once_with(test_device, group_num, *expected)
            else:
                mocked.assert_not_called()

    def test_get_flags(self, test_device):
        # This should hijack get flags and should insert a call to
        # EXTENDED_SET_GET
        with mock.patch.object(IM.CommandSeq, 'add'):
            test_device.get_flags()
            calls = [
                # TODO: figure out how to define the call to super().get_flags
                call(test_device._get_ext_flags),
            ]
            IM.CommandSeq.add.assert_has_calls(calls)
            assert IM.CommandSeq.add.call_count == 2

    def test_handle_ext_flags(self, test_device):
        from_addr = IM.Address(0x01, 0x02, 0x05)
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)
        data = bytes([0x01, 0x01, 0x00, 0x00, 0x20, 0x20, 0x1c, 0x1c, 0x1f,
                      0x00, 0x01, 0x00, 0x00, 0x00])
        msg = Msg.InpExtended(from_addr, test_device.addr, flags,
                              Msg.CmdType.EXTENDED_SET_GET, 0x00, data)
        def on_done(success, *args):
            assert success
        test_device.handle_ext_flags(msg, on_done)
        assert test_device.get_on_level() == 0x1C
