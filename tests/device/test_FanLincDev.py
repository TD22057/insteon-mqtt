#===========================================================================
#
# Tests for: insteont_mqtt/device/FanLinc.py
#
#===========================================================================
import pytest
# from pprint import pprint
from unittest import mock
from unittest.mock import call
import insteon_mqtt as IM
import insteon_mqtt.device.FanLinc as FanLinc
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
    device = FanLinc(protocol, modem, addr)
    return device


class Test_Base_Config():
    def test_pair(self, test_device):
        with mock.patch.object(IM.CommandSeq, 'add'):
            test_device.pair()
            calls = [
                call(test_device.refresh),
            ]
            IM.CommandSeq.add.assert_has_calls(calls)
            assert IM.CommandSeq.add.call_count == 1

    def test_broadcast(self, test_device, caplog):
        # test broadcast Messages, fanlinc doesn't handle any
        flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
        group = IM.Address(0x00, 0x00, 0x01)
        addr = IM.Address(0x01, 0x02, 0x03)
        msg = Msg.InpStandard(addr, group, flags, 0x11, 0x00)
        test_device.handle_broadcast(msg)
        assert "has no handler for broadcast" in caplog.text
