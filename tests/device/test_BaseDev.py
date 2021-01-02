#===========================================================================
#
# Tests for: insteont_mqtt/device/Base.py
#
#===========================================================================
import pytest
# from pprint import pprint
from unittest import mock
from unittest.mock import call
import insteon_mqtt as IM
import insteon_mqtt.device.Base as Base
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
    device = Base(protocol, modem, addr)
    return device


class Test_Base_Config():
    def test_type(self, test_device):
        assert test_device.type() == "base"

    def test_no_name(self, test_device):
        protocol = test_device.protocol
        modem = test_device.modem
        #address is intentionall badly formatted
        device = Base.from_config(["3 2.34:56"], protocol, modem)
        assert device

    def test_with_name(self, test_device):
        protocol = test_device.protocol
        modem = test_device.modem
        #address is intentionall badly formatted
        device = Base.from_config([{"32 34 56": 'test'}], protocol, modem)
        assert device

    def test_info_entry(self, test_device):
        assert test_device.info_entry() == {'01.02.03':
                                            {'label': None,
                                             'type': 'base'}
                                            }

    def test_print_db(self, test_device):
        # This just prints an output just make sure we don't crash
        test_device.print_db(util.make_callback(None))
        assert True

    def test_pair(self, test_device):
        with mock.patch.object(IM.CommandSeq, 'add'):
            test_device.pair()
            calls = [
                call(test_device.refresh),
            ]
            IM.CommandSeq.add.assert_has_calls(calls)
            assert IM.CommandSeq.add.call_count == 1

    def test_broadcast(self, test_device, caplog):
        # test broadcast Messages, Base doesn't handle any
        flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
        group = IM.Address(0x00, 0x00, 0x01)
        addr = IM.Address(0x01, 0x02, 0x03)
        msg = Msg.InpStandard(addr, group, flags, 0x11, 0x00)
        test_device.handle_broadcast(msg)
        assert "has no handler for broadcast" in caplog.text
