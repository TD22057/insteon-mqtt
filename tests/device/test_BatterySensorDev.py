#===========================================================================
#
# Tests for: insteont_mqtt/device/BatterySensor.py
#
# pylint: disable=W0621,W0212
#===========================================================================
from unittest import mock
from unittest.mock import call
import pytest
# from pprint import pprint
import insteon_mqtt as IM
import insteon_mqtt.device as Device
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
    device = Device.BatterySensor(protocol, modem, addr)
    return device


class Test_Base_Config():
    def test_pair(self, test_device):
        with mock.patch.object(IM.CommandSeq, 'add') as mocked:
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
            mocked.assert_has_calls(calls)
            assert mocked.call_count == 4

    @pytest.mark.parametrize("cmd1,expected", [
        (Msg.CmdType.ON, True),
        (Msg.CmdType.OFF, False),
        (Msg.CmdType.LINK_CLEANUP_REPORT, None),
    ])
    def test_broadcast_1(self, test_device, cmd1, expected):
        with mock.patch.object(Device.BatterySensor, '_set_is_on') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x01)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, cmd1, 0x00)
            test_device.handle_broadcast(msg)
            if expected is not None:
                mocked.assert_called_once_with(expected)
            else:
                mocked.assert_not_called()

    @pytest.mark.parametrize("cmd1,expected", [
        (Msg.CmdType.ON, True),
        (Msg.CmdType.OFF, False),
        (Msg.CmdType.LINK_CLEANUP_REPORT, None),
    ])
    def test_broadcast_3(self, test_device, cmd1, expected):
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x03)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, cmd1, 0x00)
            test_device.handle_broadcast(msg)
            if expected is not None:
                mocked.assert_called_once_with(test_device, expected)
            else:
                mocked.assert_not_called()

    @pytest.mark.parametrize("cmd1,expected", [
        (Msg.CmdType.ON, True),
        (Msg.CmdType.OFF, True),
        (Msg.CmdType.LINK_CLEANUP_REPORT, None),
    ])
    def test_broadcast_4(self, test_device, cmd1, expected):
        with mock.patch.object(IM.Signal, 'emit') as mocked:
            flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
            group = IM.Address(0x00, 0x00, 0x04)
            addr = IM.Address(0x01, 0x02, 0x03)
            msg = Msg.InpStandard(addr, group, flags, cmd1, 0x00)
            test_device.handle_broadcast(msg)
            if expected is not None:
                mocked.assert_called_once_with(test_device, expected)
            else:
                mocked.assert_not_called()

    def test_pop_queue_and_awake1(self, test_device):
        # test with empty queue
        test_device._pop_send_queue()
        assert len(test_device.protocol.sent) == 0
        #Queue a message
        msg = Msg.OutStandard.direct(test_device.addr, 0x11, 0xff)
        msg_handler = IM.handler.StandardCmd(msg, None, None)
        test_device.send(msg, msg_handler)
        # Message hasn't been sent and is queued
        assert len(test_device.protocol.sent) == 0
        assert len(test_device._send_queue) == 1
        # Pretend we got a message from the device and none already sending
        test_device.protocol.addr_in_queue = False
        test_device._pop_send_queue()
        assert len(test_device.protocol.sent) == 1
        assert len(test_device._send_queue) == 0
        assert msg_handler._num_retry == 0

    def test_pop_queue_and_awake2(self, test_device):
        #Queue a message
        msg = Msg.OutStandard.direct(test_device.addr, 0x11, 0xff)
        msg_handler = IM.handler.StandardCmd(msg, None, None)
        test_device.send(msg, msg_handler)
        # Pretend we got a message from the device and one already sending
        test_device.protocol.addr_in_queue = True
        test_device._pop_send_queue()
        assert len(test_device.protocol.sent) == 0
        assert len(test_device._send_queue) == 1

    def test_pop_queue_and_awake3(self, test_device):
        #Queue a message
        msg = Msg.OutStandard.direct(test_device.addr, 0x11, 0xff)
        msg_handler = IM.handler.StandardCmd(msg, None, None)
        test_device.send(msg, msg_handler)
        # Pretend we called awake
        def on_done(*args):
            pass
        test_device.awake(on_done)
        assert len(test_device.protocol.sent) == 1
        assert len(test_device._send_queue) == 0
        assert msg_handler._num_retry > 0
