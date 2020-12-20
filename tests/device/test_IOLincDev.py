#===========================================================================
#
# Tests for: insteont_mqtt/device/IOLinc.py
#
#===========================================================================
import pytest
from pprint import pprint
try:
    import mock
except ImportError:
    from unittest import mock
from unittest.mock import call
import insteon_mqtt as IM
import insteon_mqtt.device.IOLinc as IOLinc
import insteon_mqtt.message as Msg


@pytest.fixture
def test_iolinc(tmpdir):
    '''
    Returns a generically configured iolinc for testing
    '''
    protocol = MockProto()
    modem = MockModem(tmpdir)
    addr = IM.Address(0x01, 0x02, 0x03)
    iolinc = IOLinc(protocol, modem, addr)
    return iolinc


class Test_IOLinc_Simple():
    def test_type(self, test_iolinc):
        assert test_iolinc.type() == "io_linc"

    def test_pair(self, test_iolinc):
        with mock.patch.object(IM.CommandSeq, 'add'):
            test_iolinc.pair()
            calls = [
                call(test_iolinc.refresh),
                call(test_iolinc.db_add_ctrl_of, 0x01, test_iolinc.modem.addr, 0x01,
                     refresh=False)
            ]
            IM.CommandSeq.add.assert_has_calls(calls)
            assert IM.CommandSeq.add.call_count  == 2

    def test_get_flags(self, test_iolinc):
        with mock.patch.object(IM.CommandSeq, 'add_msg'):
            test_iolinc.get_flags()
            args_list = IM.CommandSeq.add_msg.call_args_list
            # Check that the first call is for standard flags
            # Call#, Args, First Arg
            assert args_list[0][0][0].cmd1 == 0x1f
            # Check that the second call is for momentary timeout
            assert args_list[1][0][0].cmd1 == 0x2e
            assert IM.CommandSeq.add_msg.call_count == 2

    def test_refresh(self, test_iolinc):
        with mock.patch.object(IM.CommandSeq, 'add_msg'):
            test_iolinc.refresh()
            calls = IM.CommandSeq.add_msg.call_args_list
            assert calls[0][0][0].cmd2 == 0x00
            assert calls[1][0][0].cmd2 == 0x01
            assert IM.CommandSeq.add_msg.call_count == 2


class Test_IOLinc_Set_Flags():
    def test_set_flags_empty(self, test_iolinc):
        with mock.patch.object(IM.CommandSeq, 'add_msg'):
            test_iolinc.set_flags(None)
            assert IM.CommandSeq.add_msg.call_count == 0

    def test_set_flags_unknown(self, test_iolinc):
        with pytest.raises(Exception):
            test_iolinc.trigger_reverse = 0
            with mock.patch.object(IM.CommandSeq, 'add_msg'):
                test_iolinc.set_flags(None, Unknown=1)
                assert IM.CommandSeq.add_msg.call_count == 0

    @pytest.mark.parametrize("mode,expected", [
        ("latching", [0x07, 0x13, 0x15]),
        ("momentary_a", [0x06, 0x13, 0x15]),
        ("momentary_b", [0x06, 0x12, 0x15]),
        ("momentary_c", [0x06, 0x12, 0x14]),
        ("bad-mode", [0x07, 0x13, 0x15]),
    ])
    def test_set_flags_mode(self, test_iolinc, mode, expected):
        self.mode = IM.device.IOLinc.Modes.LATCHING
        with mock.patch.object(IM.CommandSeq, 'add_msg'):
            test_iolinc.set_flags(None, mode=mode)
            # Check that the first call is for standard flags
            # Call#, Args, First Arg
            calls = IM.CommandSeq.add_msg.call_args_list
            for i in range(3):
                assert calls[i][0][0].cmd1 == 0x20
                assert calls[i][0][0].cmd2 == expected[i]
            assert IM.CommandSeq.add_msg.call_count == 3

    @pytest.mark.parametrize("flag,expected", [
        ({"trigger_reverse": 0},   [0x20, 0x0f]),
        ({"trigger_reverse": 1},   [0x20, 0x0e]),
        ({"relay_linked": 0},      [0x20, 0x05]),
        ({"relay_linked": 1},      [0x20, 0x04]),
        ({"momentary_secs": .1},   [0x2e, 0x00, 0x01, 0x01]),
        ({"momentary_secs": 26},   [0x2e, 0x00, 0x1a, 0x0a]),
        ({"momentary_secs": 260},  [0x2e, 0x00, 0x1a, 0x64]),
        ({"momentary_secs": 3000}, [0x2e, 0x00, 0x96, 0xc8]),
        ({"momentary_secs": 6300}, [0x2e, 0x00, 0xfc, 0xfa]),
    ])
    def test_set_flags_other(self, test_iolinc, flag, expected):
        test_iolinc.momentary_secs = 0
        test_iolinc.relay_linked = 0
        test_iolinc.trigger_reverse = 0
        with mock.patch.object(IM.CommandSeq, 'add_msg'):
            test_iolinc.set_flags(None, **flag)
            # Check that the first call is for standard flags
            # Call#, Args, First Arg
            calls = IM.CommandSeq.add_msg.call_args_list
            assert calls[0][0][0].cmd1 == expected[0]
            assert calls[0][0][0].cmd2 == expected[1]
            if len(expected) > 2:
                assert calls[0][0][0].data[1] == 0x06
                assert calls[0][0][0].data[2] == expected[2]
                assert calls[1][0][0].data[1] == 0x07
                assert calls[1][0][0].data[2] == expected[3]
                assert IM.CommandSeq.add_msg.call_count == 2
            else:
                assert IM.CommandSeq.add_msg.call_count == 1


class Test_IOLinc_Set():
    @pytest.mark.parametrize("level,expected", [
        (0x00, 0x13),
        (0x01, 0x11),
        (0xff, 0x11),
    ])
    def test_set(self, test_iolinc, level, expected):
        with mock.patch.object(IM.device.Base, 'send'):
            test_iolinc.set(level)
            calls = IM.device.Base.send.call_args_list
            assert calls[0][0][0].cmd1 == expected
            assert IM.device.Base.send.call_count == 1

    @pytest.mark.parametrize("is_on,expected", [
        (True, True),
        (False, False),
    ])
    def test_sensor_on(self, test_iolinc, is_on, expected):
        with mock.patch.object(IM.Signal, 'emit'):
            test_iolinc._set_sensor_is_on(is_on)
            calls = IM.Signal.emit.call_args_list
            assert calls[0][0][1] == expected
            assert IM.Signal.emit.call_count == 1

    @pytest.mark.parametrize("is_on, mode, moment, relay, add, remove", [
        (True, IM.device.IOLinc.Modes.LATCHING, False, True, 0, 0),
        (True, IM.device.IOLinc.Modes.MOMENTARY_A, False, True, 1, 0),
        (True, IM.device.IOLinc.Modes.MOMENTARY_A, False, True, 1, 1),
        (False, IM.device.IOLinc.Modes.MOMENTARY_A, False, False, 0, 0),
        (False, IM.device.IOLinc.Modes.MOMENTARY_A, True, False, 0, 0),
        (False, IM.device.IOLinc.Modes.MOMENTARY_A, True, False, 0, 1),
    ])
    def test_relay_on(self, test_iolinc, is_on, mode, moment, relay,
                      add, remove):
        with mock.patch.object(IM.Signal, 'emit'):
            with mock.patch.object(test_iolinc.modem.timed_call, 'add'):
                with mock.patch.object(test_iolinc.modem.timed_call, 'remove'):
                    test_iolinc.mode = mode
                    if remove > 0:
                        test_iolinc._momentary_call = True
                    test_iolinc._set_relay_is_on(is_on, momentary=moment)
                    emit_calls = IM.Signal.emit.call_args_list
                    assert emit_calls[0][0][2] == relay
                    assert IM.Signal.emit.call_count == 1
                    assert test_iolinc.modem.timed_call.add.call_count == add
                    assert test_iolinc.modem.timed_call.remove.call_count == remove

class Test_Handles():
    @pytest.mark.parametrize("linked,cmd1,sensor,relay", [
        (False, 0x11, True, None),
        (True, 0x11, True, True),
        (False, 0x13, False, None),
        (True, 0x13, False, False),
        (False, 0x06, None, None),
    ])
    def test_handle_broadcast(self, test_iolinc, linked, cmd1, sensor,
                              relay):
        with mock.patch.object(IM.Signal, 'emit'):
            test_iolinc.relay_linked = linked
            to_addr = IM.Address(0x00, 0x00, 0x01)
            from_addr = IM.Address(0x04, 0x05, 0x06)
            flags = IM.message.Flags(IM.message.Flags.Type.ALL_LINK_BROADCAST,
                                     False)
            cmd2 = 0x00
            msg = IM.message.InpStandard(from_addr, to_addr, flags, cmd1, cmd2)
            test_iolinc.handle_broadcast(msg)
            calls = IM.Signal.emit.call_args_list
            if linked:
                assert calls[1][0][2] == relay
                assert IM.Signal.emit.call_count == 2
            elif sensor is not None:
                assert calls[0][0][1] == sensor
                assert IM.Signal.emit.call_count == 1
            else:
                assert IM.Signal.emit.call_count == 0

    @pytest.mark.parametrize("cmd1,expected", [
        (Msg.CmdType.LINK_CLEANUP_REPORT, None),
    ])
    def test_broadcast_2(self, test_iolinc, cmd1, expected):
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x04)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, cmd1, 0x00)
            test_iolinc.handle_broadcast(msg)
            if expected is not None:
                mocked.assert_called_once_with(test_device, expected)
            else:
                mocked.assert_not_called()

    @pytest.mark.parametrize("cmd2,mode,relay,reverse", [
        (0x00, IM.device.IOLinc.Modes.LATCHING, False, False),
        (0X0c, IM.device.IOLinc.Modes.MOMENTARY_A, True, False),
        (0x5c, IM.device.IOLinc.Modes.MOMENTARY_B, True, True),
        (0xd8, IM.device.IOLinc.Modes.MOMENTARY_C, False, True),
    ])
    def test_handle_flags(self, test_iolinc, cmd2, mode, relay,
                          reverse):
        to_addr = test_iolinc.addr
        from_addr = IM.Address(0x04, 0x05, 0x06)
        flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
        cmd1 = 0x1f
        msg = IM.message.InpStandard(from_addr, to_addr, flags, cmd1, cmd2)
        test_iolinc.handle_flags(msg, lambda success, msg, cmd: True)
        assert test_iolinc.mode == mode
        assert test_iolinc.relay_linked == relay
        assert test_iolinc.trigger_reverse == reverse

    @pytest.mark.parametrize("time_val, multiplier, seconds", [
        (0x01, 0x01, .1),
        (0x1a, 0x0a, 26),
        (0x1a, 0x64, 260),
        (0x96, 0xc8, 3000),
        (0xfc, 0xfa, 6300),
    ])
    def test_handle_momentary(self, test_iolinc, time_val, multiplier,
                              seconds):
        to_addr = test_iolinc.addr
        from_addr = IM.Address(0x04, 0x05, 0x06)
        flags = IM.message.Flags(IM.message.Flags.Type.DIRECT, True)
        data = bytes([0x00] * 2 + [multiplier, time_val] + [0x00] * 10)
        msg = IM.message.InpExtended(from_addr, to_addr, flags, 0x2e, 0x00,
                                     data)
        test_iolinc.handle_get_momentary(msg, lambda success, msg, cmd: True)
        assert test_iolinc.momentary_secs == seconds

    def test_handle_set_flags(self, test_iolinc):
        # Dummy Test, nothing to do here
        to_addr = test_iolinc.addr
        from_addr = IM.Address(0x04, 0x05, 0x06)
        flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
        msg = IM.message.InpStandard(from_addr, to_addr, flags, 0x00, 0x00)
        test_iolinc.handle_set_flags(msg, lambda success, msg, cmd: True)
        assert True == True

    @pytest.mark.parametrize("cmd2,expected", [
        (0x00, False),
        (0Xff, True),
    ])
    def test_handle_refresh_relay(self, test_iolinc, cmd2, expected):
        with mock.patch.object(IM.Signal, 'emit'):
            to_addr = test_iolinc.addr
            from_addr = IM.Address(0x04, 0x05, 0x06)
            flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
            msg = IM.message.InpStandard(from_addr, to_addr, flags, 0x19, cmd2)
            test_iolinc.handle_refresh_relay(msg)
            calls = IM.Signal.emit.call_args_list
            assert calls[0][0][2] == expected
            assert IM.Signal.emit.call_count == 1

    @pytest.mark.parametrize("cmd2,expected", [
        (0x00, False),
        (0Xff, True),
    ])
    def test_handle_refresh_sensor(self, test_iolinc, cmd2, expected):
        with mock.patch.object(IM.Signal, 'emit'):
            to_addr = test_iolinc.addr
            from_addr = IM.Address(0x04, 0x05, 0x06)
            flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
            msg = IM.message.InpStandard(from_addr, to_addr, flags, 0x19, cmd2)
            test_iolinc.handle_refresh_sensor(msg)
            calls = IM.Signal.emit.call_args_list
            assert calls[0][0][1] == expected
            assert IM.Signal.emit.call_count == 1

    @pytest.mark.parametrize("cmd1, type, expected", [
        (0x11, IM.message.Flags.Type.DIRECT_ACK, True),
        (0X13, IM.message.Flags.Type.DIRECT_ACK, False),
    ])
    def test_handle_ack(self, test_iolinc, cmd1, type, expected):
        with mock.patch.object(IM.Signal, 'emit'):
            to_addr = test_iolinc.addr
            from_addr = IM.Address(0x04, 0x05, 0x06)
            flags = IM.message.Flags(type, False)
            msg = IM.message.InpStandard(from_addr, to_addr, flags, cmd1, 0x01)
            test_iolinc.handle_ack(msg, lambda success, msg, cmd: True)
            calls = IM.Signal.emit.call_args_list
            assert calls[0][0][2] == expected
            assert IM.Signal.emit.call_count == 1

    @pytest.mark.parametrize("cmd1, entry_d1, mode, sensor, expected", [
        (0x11, None, IM.device.IOLinc.Modes.LATCHING, False, None),
        (0x11, 0xFF, IM.device.IOLinc.Modes.LATCHING, False, True),
        (0x13, 0xFF, IM.device.IOLinc.Modes.LATCHING, False, False),
        (0x11, 0xFF, IM.device.IOLinc.Modes.MOMENTARY_A, False, True),
        (0x13, 0xFF, IM.device.IOLinc.Modes.MOMENTARY_A, False, False),
        (0x11, 0x00, IM.device.IOLinc.Modes.MOMENTARY_A, False, False),
        (0x13, 0x00, IM.device.IOLinc.Modes.MOMENTARY_A, False, True),
        (0x11, 0xFF, IM.device.IOLinc.Modes.MOMENTARY_B, False, True),
        (0x13, 0xFF, IM.device.IOLinc.Modes.MOMENTARY_B, False, True),
        (0x11, 0xFF, IM.device.IOLinc.Modes.MOMENTARY_C, False, False),
        (0x13, 0xFF, IM.device.IOLinc.Modes.MOMENTARY_C, False, True),
        (0x11, 0X00, IM.device.IOLinc.Modes.MOMENTARY_C, False, True),
        (0x13, 0X00, IM.device.IOLinc.Modes.MOMENTARY_C, False, False),
        (0x11, 0xFF, IM.device.IOLinc.Modes.MOMENTARY_C, True, True),
        (0x13, 0xFF, IM.device.IOLinc.Modes.MOMENTARY_C, True, False),
        (0xFF, 0xFF, IM.device.IOLinc.Modes.MOMENTARY_C, True, None),
    ])
    def test_handle_group_cmd(self, test_iolinc, cmd1, entry_d1, mode,
                              sensor, expected):
        # We null out the TimedCall feature with a Mock class below.  We could
        # test here, but I wrote a specific test of the set functions instead
        # Attach to signal sent to MQTT
        with mock.patch.object(IM.Signal, 'emit'):
            # Set the device in the requested states
            test_iolinc._sensor_is_on = sensor
            test_iolinc.mode = mode
            # Build the msg to send to the handler
            to_addr = test_iolinc.addr
            from_addr = IM.Address(0x04, 0x05, 0x06)
            flags = IM.message.Flags(IM.message.Flags.Type.ALL_LINK_CLEANUP,
                                     False)
            msg = IM.message.InpStandard(from_addr, to_addr, flags, cmd1, 0x01)
            # If db entry is requested, build and add the entry to the dev db
            if entry_d1 is not None:
                db_flags = IM.message.DbFlags(True, False, True)
                entry = IM.db.DeviceEntry(from_addr, 0x01, 0xFFFF, db_flags,
                                          bytes([entry_d1, 0x00, 0x00]))
                test_iolinc.db.add_entry(entry)
            # send the message to the handler
            test_iolinc.handle_group_cmd(from_addr, msg)
            # Test the responses received
            calls = IM.Signal.emit.call_args_list
            if expected is not None:
                assert calls[0][0][2] == expected
                assert IM.Signal.emit.call_count == 1
            else:
                assert IM.Signal.emit.call_count == 0


class Test_IOLinc_Link_Data:
    @pytest.mark.parametrize("data_1, pretty_data_1, name, is_controller", [
        (0x00, 0, 'on_off', False),
        (0xFF, 1, 'on_off', False),
        (0xFF, 0XFF, 'data_1', True),
    ])
    def test_link_data(self, test_iolinc, data_1, pretty_data_1, name,
                       is_controller):
        pretty = test_iolinc.link_data_to_pretty(is_controller,
                                                 [data_1, 0x00, 0x00])
        assert pretty[0][name] == pretty_data_1
        ugly = test_iolinc.link_data_from_pretty(is_controller,
                                                 {name: pretty_data_1,
                                                  'data_2': 0x00,
                                                  'data_3': 0x00})
        assert ugly[0] == data_1


class MockModem:
    def __init__(self, path):
        self.save_path = str(path)
        self.addr = IM.Address(0x0A, 0x0B, 0x0C)
        self.timed_call = MockTimedCall()


class MockTimedCall:
    def add(self, *args, **kwargs):
        pass

    def remove(self, *args, **kwargs):
        pass

class MockProto:
    def __init__(self):
        self.msgs = []
        self.wait = None

    def add_handler(self, *args):
        pass

    def send(self, msg, msg_handler, high_priority=False, after=None):
        self.msgs.append(msg)

    def set_wait_time(self, time):
        self.wait = time
