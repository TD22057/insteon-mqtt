#===========================================================================
#
# Tests for: insteont_mqtt/device/Dimmer.py
#
#===========================================================================
import pytest
# from pprint import pprint
from unittest import mock
from unittest.mock import call
import insteon_mqtt as IM
import insteon_mqtt.device.Dimmer as Dimmer
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
    device = Dimmer(protocol, modem, addr)
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
        (0x01,Msg.CmdType.ON, 0x00,{"level":255,"is_on":True,"mode":IM.on_off.Mode.NORMAL, "button":1, "reason":'device'}),
        (0x01,Msg.CmdType.OFF, 0x00, {"level":0,"is_on":False,"mode":IM.on_off.Mode.NORMAL, "button":1, "reason":'device'}),
        (0x01,Msg.CmdType.ON_FAST, 0x00,{"level":255,"is_on":True,"mode":IM.on_off.Mode.FAST, "button":1, "reason":'device'}),
        (0x01,Msg.CmdType.OFF_FAST, 0x00, {"level":0,"is_on":False,"mode":IM.on_off.Mode.FAST, "button":1, "reason":'device'}),
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

    @pytest.mark.parametrize("group,cmd1,cmd2,expected", [
        (0x01,Msg.CmdType.START_MANUAL_CHANGE, 0x00, {"manual":IM.on_off.Manual.DOWN, "button":1, "reason":'device'}),
        (0x01,Msg.CmdType.START_MANUAL_CHANGE, 0x01, {"manual":IM.on_off.Manual.UP, "button":1, "reason":'device'}),
        (0x01,Msg.CmdType.STOP_MANUAL_CHANGE, 0x00, {"manual":IM.on_off.Manual.STOP, "button":1, "reason":'device'}),
    ])
    def test_handle_on_off_manual(self, test_device, group, cmd1, cmd2, expected):
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

    def test_set_resume_dim_non_i2cs(self, test_device):
        # set_resume_dim(self, resume_dim, on_done=None)
        for params in ([True, 0x04], [False, 0x05]):
            test_device.set_resume_dim(resume_dim=params[0])
            assert len(test_device.protocol.sent) == 1
            assert isinstance(test_device.protocol.sent[0].msg, Msg.OutStandard)
            assert test_device.protocol.sent[0].msg.cmd1 == 0x20
            assert test_device.protocol.sent[0].msg.cmd2 == params[1]
            test_device.protocol.clear()

    def test_set_resume_dim_unknown(self, test_device):
        # set_resume_dim(self, resume_dim, on_done=None)
        test_device.db.engine = None
        for params in ([True, 0x04], [False, 0x05]):
            test_device.set_resume_dim(resume_dim=params[0])
            assert len(test_device.protocol.sent) == 1
            assert isinstance(test_device.protocol.sent[0].msg, Msg.OutStandard)
            assert test_device.protocol.sent[0].msg.cmd1 == 0x20
            assert test_device.protocol.sent[0].msg.cmd2 == params[1]
            test_device.protocol.clear()
            
    def test_set_resume_dim_i2cs(self, test_device):
        # set_resume_dim(self, resume_dim, on_done=None)
        test_device.db.engine = 2
        for params in ([True, 0x04], [False, 0x05]):
            test_device.set_resume_dim(resume_dim=params[0])
            assert len(test_device.protocol.sent) == 1
            assert isinstance(test_device.protocol.sent[0].msg, Msg.OutExtended)
            assert test_device.protocol.sent[0].msg.cmd1 == 0x20
            assert test_device.protocol.sent[0].msg.cmd2 == params[1]
            assert test_device.protocol.sent[0].msg.data == bytes([0x00] * 14)
            test_device.protocol.clear()

    def test_set_on_level(self, test_device):
        # set_on_level(self, level, on_done=None)
        def level_bytes(level):
            data = bytes([
                0x01,
                0x06,
                level,
                ] + [0x00] * 11)
            return data
        assert(test_device.get_on_level() == 255)
        for params in ([1, 0x01], [127, 127], [255, 0xFF]):
            test_device.set_on_level(on_level=params[0])
            assert len(test_device.protocol.sent) == 1
            assert test_device.protocol.sent[0].msg.cmd1 == 0x2e
            assert (test_device.protocol.sent[0].msg.data ==
                    level_bytes(params[1]))
            test_device.protocol.clear()

        test_device.set_on_level(on_level=64)

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
            (Msg.CmdType.ON, 0x00, {"level":64, "is_on":True, "mode":IM.on_off.Mode.NORMAL, "button":1, "reason":'device'}),
            (Msg.CmdType.ON, 0x00, {"level":255, "is_on":True, "mode":IM.on_off.Mode.NORMAL, "button":1, "reason":'device'}),
            (Msg.CmdType.ON, 0x00, {"level":64, "is_on":True, "mode":IM.on_off.Mode.NORMAL, "button":1, "reason":'device'}),
            (Msg.CmdType.OFF, 0x00, {"level":0, "is_on":False, "mode":IM.on_off.Mode.NORMAL, "button":1, "reason":'device'}),
            (Msg.CmdType.ON_FAST, 0x00, {"level":255, "is_on":True,
                                         "mode":IM.on_off.Mode.FAST,
                                         "button":1, "reason":'device'}),
            (Msg.CmdType.ON_FAST, 0x00, {"level":255, "is_on":True,
                                         "mode":IM.on_off.Mode.FAST,
                                         "button":1, "reason":'device'}),
            (Msg.CmdType.OFF_FAST, 0x00, {"level":0, "is_on":False, "mode":IM.on_off.Mode.FAST, "button":1, "reason":'device'}),
            (Msg.CmdType.ON_INSTANT, 0x00,
                {"level":64, "is_on":True, "mode":IM.on_off.Mode.INSTANT, "button":1, "reason":'device'}),
            (Msg.CmdType.ON_INSTANT, 0x00,
                {"level":255, "is_on":True, "mode": IM.on_off.Mode.INSTANT, "button":1, "reason":'device'}),
            (Msg.CmdType.ON_INSTANT, 0x00,
                {"level":64, "is_on":True, "mode":IM.on_off.Mode.INSTANT, "button":1, "reason":'device'})]
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
                    mocked.assert_called_once_with(test_device, **expected)
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
