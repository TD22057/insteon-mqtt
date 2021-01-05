#===========================================================================
#
# Tests for: insteont_mqtt/Modem.py
#
#===========================================================================
import pytest
# from pprint import pprint
from unittest import mock
from unittest.mock import call
import insteon_mqtt as IM
import insteon_mqtt.message as Msg
import insteon_mqtt.util as util
import helpers as H

@pytest.fixture
def test_device():
    '''
    Returns a generically configured modem for testing
    '''
    protocol = mock.MagicMock()
    stack = H.main.MockStack()
    timed_call = H.main.MockTimedCall()
    device = IM.Modem(protocol, stack, timed_call)
    return device


class Test_Base_Config():
    def test_load_config_no_addr(self, test_device):
        cfg = IM.config.load('config.yaml')
        test_device.load_config(cfg)
        # Protocol should load
        test_device.protocol.load_config.assert_called_once_with(cfg)
        assert test_device.addr is None
        test_device.protocol.send.assert_called_once()
        arg_list = test_device.protocol.send.call_args
        assert isinstance(arg_list.args[0], Msg.OutModemInfo)
        assert isinstance(arg_list.args[1], IM.handler.ModemInfo)

    def test_load_config_addr(self, test_device):
        cfg = IM.config.load('config.yaml')
        cfg['address'] = '44.85.11'
        test_device.load_config(cfg)
        assert test_device.addr == IM.Address('44.85.11')

    def test_load_config_step2_fail_no_addr(self, test_device, tmpdir):
        cfg = IM.config.load('config.yaml')
        cfg['storage'] = tmpdir
        with mock.patch('sys.exit') as mocked:
            test_device.load_config_step2(False, 'message', None, cfg)
            mocked.assert_called_once()

    def test_load_config_step2_fail_addr(self, test_device, tmpdir, caplog):
        cfg = IM.config.load('config.yaml')
        cfg['storage'] = tmpdir
        test_device.addr = IM.Address('44.85.11')
        test_device.load_config_step2(False, 'message', None, cfg)
        assert 'Unable to get modem address, using address in' in caplog.text

    def test_load_config_step2_success_addr_same(self, test_device, tmpdir,
                                                 caplog):
        cfg = IM.config.load('config.yaml')
        cfg['storage'] = tmpdir
        test_device.addr = IM.Address('44.85.11')
        msg = Msg.OutModemInfo(addr=test_device.addr, dev_cat=None,
                               sub_cat=None, firmware=None, is_ack=True)
        test_device.load_config_step2(True, 'message', msg, cfg)
        for record in caplog.records:
            assert record.levelname != "ERROR"

    def test_load_config_step2_success_addr_diff(self, test_device, tmpdir,
                                                 caplog):
        cfg = IM.config.load('config.yaml')
        cfg['storage'] = tmpdir
        test_device.addr = IM.Address('44.85.11')
        msg = Msg.OutModemInfo(addr=IM.Address('44.85.12'), dev_cat=None,
                               sub_cat=None, firmware=None, is_ack=True)
        test_device.load_config_step2(True, 'message', msg, cfg)
        assert 'Modem address in config 44.85.11 does not match address' in caplog.text

    def test_load_config_step2_success_no_addr(self, test_device, tmpdir,
                                               caplog):
        cfg = IM.config.load('config.yaml')
        cfg['storage'] = tmpdir
        msg = Msg.OutModemInfo(addr=IM.Address('44.85.12'), dev_cat=None,
                               sub_cat=None, firmware=None, is_ack=True)
        test_device.load_config_step2(True, 'message', msg, cfg)
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert test_device.addr == IM.Address('44.85.12')
