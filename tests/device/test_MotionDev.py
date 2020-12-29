#===========================================================================
#
# Tests for: insteont_mqtt/device/Motion.py
#
# pylint: disable=W0621,W0201,W0212
#===========================================================================
from unittest import mock
from unittest.mock import call
import pytest
# from pprint import pprint
import insteon_mqtt as IM
import insteon_mqtt.device.Motion as Motion
import insteon_mqtt.message as Msg
# import insteon_mqtt.util as util
import helpers as H

@pytest.fixture
def test_device(tmpdir):
    '''
    Returns a generically configured iolinc for testing
    '''
    protocol = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    addr = IM.Address(0x01, 0x02, 0x03)
    device = Motion(protocol, modem, addr)
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
                call(test_device.db_add_ctrl_of, 0x04, test_device.modem.addr, 0x01,
                     refresh=False),
                     ]
            IM.CommandSeq.add.assert_has_calls(calls, any_order=True)
            assert IM.CommandSeq.add.call_count == 5

    @pytest.mark.parametrize("group_num,cmd1,cmd2,expected", [
        (0x01,Msg.CmdType.ON, 0x00,[True]),
        (0x01,Msg.CmdType.OFF, 0x00, [False]),
        (0x01,Msg.CmdType.LINK_CLEANUP_REPORT, 0x00, None),
        (0x02,Msg.CmdType.ON, 0x00,[True]),
        (0x02,Msg.CmdType.OFF, 0x00, [False]),
        (0x02,Msg.CmdType.LINK_CLEANUP_REPORT, 0x00, None),
        (0x03,Msg.CmdType.ON, 0x00,[True]),
        (0x03,Msg.CmdType.OFF, 0x00, [False]),
        (0x03,Msg.CmdType.LINK_CLEANUP_REPORT, 0x00, None),
        (0x04,Msg.CmdType.ON, 0x00,[True]),
        (0x04,Msg.CmdType.OFF, 0x00, [True]),
        (0x04,Msg.CmdType.LINK_CLEANUP_REPORT, 0x00, None),
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
                mocked.assert_called_once_with(test_device, *expected)
            else:
                mocked.assert_not_called()

    def test_voltage_time(self, test_device):
        assert test_device.battery_voltage_time == 0
        test_device.battery_voltage_time = 100
        assert test_device.battery_voltage_time == 100
        test_device.battery_voltage_time = 200
        assert test_device.battery_voltage_time == 200

    def test_low_voltage(self, test_device):
        # set as a 2842 model
        test_device.db.set_info(0x10, 0x01, 0x00)
        assert test_device.battery_low_voltage == 7.0
        # set as a 2844 model
        test_device.db.set_info(0x10, 0x16, 0x00)
        assert test_device.battery_low_voltage == 1.85
        test_device.battery_low_voltage = 100
        assert test_device.battery_low_voltage == 100
        test_device.battery_low_voltage = 200
        assert test_device.battery_low_voltage == 200

    def test_set_low_voltage(self, test_device, caplog):
        def on_done(success, *args):
            assert not success
        test_device.set_low_battery_voltage(on_done)
        assert "requires voltage key" in caplog.text
        def on_done2(success, *args):
            assert success
        test_device.set_low_battery_voltage(on_done2, voltage=8.0)
        assert test_device.battery_low_voltage == 8.0

    def test_handle_ext_flags(self, test_device):
        # Captured data from my own motion detector
        # 00 01 03 00 ff 0e 00 ff 0e 01 18 4f 00 d2
        # set as a 2842 model
        test_device.db.set_info(0x10, 0x01, 0x00)
        modem_addr = IM.Address(0x01, 0xAA, 0xFF)
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)
        msg = Msg.InpExtended(test_device.addr, modem_addr, flags,
                              0x2e, 0x00,
                              bytes([0x00, 0x01, 0x03, 0x00, 0xff, 0x0e, 0x00,
                                     0xff, 0x0e, 0x01, 0x18, 0x4f, 0x00, 0xd2])
                             )
        def on_done(success, *args):
            assert success
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            test_device.handle_ext_flags(msg, on_done)
            assert test_device.led_on
            assert test_device.night_only
            assert test_device.on_only
            assert test_device.battery_voltage_time > 0
            assert mocked.call_count == 1
            # the emit call should be false
            assert not mocked.call_args.args[1]

    def test_handle_ext_flags2(self, test_device):
        # This should trigger low battery
        test_device.battery_low_voltage = 8.0
        modem_addr = IM.Address(0x01, 0xAA, 0xFF)
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)
        msg = Msg.InpExtended(test_device.addr, modem_addr, flags,
                              0x2e, 0x00,
                              bytes([0x00, 0x01, 0x03, 0x00, 0xff, 0x0e, 0x00,
                                     0xff, 0x0e, 0x01, 0x18, 0x4f, 0x00, 0xd2])
                             )
        def on_done(success, *args):
            assert success
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            test_device.handle_ext_flags(msg, on_done)
            assert test_device.led_on
            assert test_device.night_only
            assert test_device.on_only
            assert test_device.battery_voltage_time > 0
            assert mocked.call_count == 1
            # the emit call should be true
            assert mocked.call_args.args[1]

    def test_handle_ext_flags3(self, test_device, caplog):
        # set as a 2844 model
        test_device.db.set_info(0x10, 0x16, 0x00)
        modem_addr = IM.Address(0x01, 0xAA, 0xFF)
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)
        msg = Msg.InpExtended(test_device.addr, modem_addr, flags,
                              0x2e, 0x00,
                              bytes([0x00, 0x01, 0x03, 0x00, 0xff, 0x0e, 0x00,
                                     0xff, 0x0e, 0x01, 0x18, 0x8C, 0x00, 0xd2])
                             )
        def on_done(success, *args):
            assert success
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            test_device.handle_ext_flags(msg, on_done)
            assert test_device.led_on
            assert test_device.night_only
            assert test_device.on_only
            assert test_device.battery_voltage_time > 0
            assert mocked.call_count == 1
            # the emit call should be false, not a low battery for 2844
            assert not mocked.call_args.args[1]

    def test_awake(self, test_device):
        with mock.patch.object(test_device, 'auto_check_battery') as mocked:
            def on_done(*args):
                pass
            test_device.awake(on_done)
            mocked.assert_called_once()

    def test_pop_queue(self, test_device):
        with mock.patch.object(test_device, 'auto_check_battery') as mocked:
            test_device._pop_send_queue()
            mocked.assert_called_once()

    def test_auto_check_battery(self, test_device):
        # set as a 2842 model
        test_device.db.set_info(0x10, 0x01, 0x00)
        def on_done(*args):
            pass
        # Mark awake so messages get sent to protocol
        test_device.awake(on_done)
        # Run without any prior data
        test_device.auto_check_battery()
        sent = test_device.protocol.sent
        assert len(sent) == 1
        assert sent[0].msg.cmd1 == Msg.CmdType.EXTENDED_SET_GET
        assert sent[0].msg.data == bytes(14)
        assert test_device._battery_request_time > 0
        # Try again, we should get nothing
        test_device.protocol.clear()
        test_device.auto_check_battery()
        sent = test_device.protocol.sent
        assert len(sent) == 0

    def test_auto_check_battery2(self, test_device):
        # set as a 2844 model
        test_device.db.set_info(0x10, 0x16, 0x00)
        def on_done(*args):
            pass
        # Mark awake so messages get sent to protocol
        test_device.awake(on_done)
        # Run without any prior data
        test_device.auto_check_battery()
        sent = test_device.protocol.sent
        assert len(sent) == 1
        assert sent[0].msg.cmd1 == Msg.CmdType.EXTENDED_SET_GET
        assert sent[0].msg.data == bytes(14)
        assert test_device._battery_request_time > 0
        # Try again, we should get nothing
        test_device.protocol.clear()
        test_device.auto_check_battery()
        sent = test_device.protocol.sent
        assert len(sent) == 0
