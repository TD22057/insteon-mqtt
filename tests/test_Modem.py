#===========================================================================
#
# Tests for: insteont_mqtt/Modem.py
#
#===========================================================================
import logging
import pytest
# from pprint import pprint
from unittest import mock
from unittest.mock import call
import insteon_mqtt as IM
from insteon_mqtt.device.base.Base import Base
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

@pytest.fixture
def test_device_2(tmpdir):
    '''
    Returns a generically configured device for testing
    '''
    protocol = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    modem.db = IM.db.Modem(None, modem)
    modem.scenes = IM.Scenes.SceneManager(modem, None)
    addr = IM.Address(0x56, 0x78, 0xcd)
    device = Base(protocol, modem, addr)
    return device

@pytest.fixture
def test_entry_2():
    addr = IM.Address('56.78.cd')
    data = bytes([0xff, 0x00, 0x00])
    group = 0x01
    in_use = True
    is_controller = True
    is_last_rec = False
    db_flags = Msg.DbFlags(in_use, is_controller, is_last_rec)
    mem_loc = 1
    return IM.db.DeviceEntry(addr, group, mem_loc, db_flags, data)

@pytest.fixture
def test_entry_multigroup():
    addr = IM.Address('56.78.cd')
    data = bytes([0xff, 0x00, 0x00])
    group = 0x02
    in_use = True
    is_controller = True
    is_last_rec = False
    db_flags = Msg.DbFlags(in_use, is_controller, is_last_rec)
    mem_loc = 1
    return IM.db.DeviceEntry(addr, group, mem_loc, db_flags, data)

class Test_Base_Config():
    def test_load_config_no_addr(self, test_device):
        cfg = IM.config.load('config-example.yaml')
        test_device.load_config(cfg)
        # Protocol should load
        test_device.protocol.load_config.assert_called_once_with(cfg)
        assert test_device.addr is None
        test_device.protocol.send.assert_called_once()
        arg_list = test_device.protocol.send.call_args
        assert isinstance(arg_list.args[0], Msg.OutModemInfo)
        assert isinstance(arg_list.args[1], IM.handler.ModemInfo)

    def test_load_config_addr(self, test_device):
        cfg = IM.config.load('config-example.yaml')
        cfg['address'] = '44.85.11'
        test_device.load_config(cfg)
        assert test_device.addr == IM.Address('44.85.11')

    def test_load_config_step2_fail_no_addr(self, test_device, tmpdir):
        cfg = IM.config.load('config-example.yaml')
        cfg['storage'] = tmpdir
        with mock.patch('sys.exit') as mocked:
            test_device.load_config_step2(False, 'message', None, cfg)
            mocked.assert_called_once()

    def test_load_config_step2_fail_addr(self, test_device, tmpdir, caplog):
        cfg = IM.config.load('config-example.yaml')
        cfg['storage'] = tmpdir
        test_device.addr = IM.Address('44.85.11')
        test_device.load_config_step2(False, 'message', None, cfg)
        assert 'Unable to get modem address, using address in' in caplog.text

    def test_load_config_step2_success_addr_same(self, test_device, tmpdir,
                                                 caplog):
        cfg = IM.config.load('config-example.yaml')
        cfg['storage'] = tmpdir
        test_device.addr = IM.Address('44.85.11')
        msg = Msg.OutModemInfo(addr=test_device.addr, dev_cat=None,
                               sub_cat=None, firmware=None, is_ack=True)
        test_device.load_config_step2(True, 'message', msg, cfg)
        for record in caplog.records:
            assert record.levelname != "ERROR"

    def test_load_config_step2_success_addr_diff(self, test_device, tmpdir,
                                                 caplog):
        cfg = IM.config.load('config-example.yaml')
        cfg['storage'] = tmpdir
        test_device.addr = IM.Address('44.85.11')
        msg = Msg.OutModemInfo(addr=IM.Address('44.85.12'), dev_cat=None,
                               sub_cat=None, firmware=None, is_ack=True)
        test_device.load_config_step2(True, 'message', msg, cfg)
        assert 'Modem address in config 44.85.11 does not match address' in caplog.text

    def test_load_config_step2_success_no_addr(self, test_device, tmpdir,
                                               caplog):
        cfg = IM.config.load('config-example.yaml')
        cfg['storage'] = tmpdir
        msg = Msg.OutModemInfo(addr=IM.Address('44.85.12'), dev_cat=None,
                               sub_cat=None, firmware=None, is_ack=True)
        test_device.load_config_step2(True, 'message', msg, cfg)
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert test_device.addr == IM.Address('44.85.12')

    def test_db_update(self, test_device, test_entry_2,
                       test_device_2, caplog):
        test_device.add(test_device_2)
        with mock.patch.object(IM.CommandSeq, 'add') as mocked:
            with caplog.at_level(logging.DEBUG):
                two_way = True
                refresh = True
                test_device._db_update(test_entry_2.group,
                                       test_entry_2.is_controller,
                                       test_entry_2.addr,
                                       test_entry_2.group,
                                       two_way,
                                       refresh,
                                       None,
                                       bytes([0x00, 0x00, 0x00]),
                                       test_entry_2.data)
                assert mocked.call_count == 2
                call_args = mocked.call_args_list
                assert call_args[0].args[0] == test_device.db.add_on_device
                assert call_args[0].args[1].addr == test_entry_2.addr
                assert call_args[0].args[1].group == test_entry_2.group
                assert call_args[0].args[1].is_controller == test_entry_2.is_controller
                assert call_args[0].args[1].data == bytes([0x00, 0x00, 0x00])
                assert call_args[1] == call(test_device_2.db_add_resp_of, 
                                            test_entry_2.group,
                                            test_device.addr, test_entry_2.group, 
                                            False,
                                            refresh, local_data=test_entry_2.data)

    def test_db_update_resp(self, test_device, test_entry_2,
                            test_device_2, caplog):
        test_device.add(test_device_2)
        with mock.patch.object(IM.CommandSeq, 'add') as mocked:
            with caplog.at_level(logging.DEBUG):
                two_way = True
                refresh = True
                test_device._db_update(test_entry_2.group,
                                       False,
                                       test_entry_2.addr,
                                       test_entry_2.group,
                                       two_way,
                                       refresh,
                                       None,
                                       bytes([0x00, 0x00, 0x00]),
                                       test_entry_2.data)
                assert mocked.call_count == 2
                call_args = mocked.call_args_list
                assert call_args[0].args[0] == test_device.db.add_on_device
                assert call_args[0].args[1].addr == test_entry_2.addr
                assert call_args[0].args[1].group == test_entry_2.group
                assert call_args[0].args[1].is_controller == False
                assert call_args[0].args[1].data == bytes([0x00, 0x00, 0x00])
                assert call_args[1] == call(test_device_2.db_add_ctrl_of, test_entry_2.group,
                                            test_device.addr, test_entry_2.group, False,
                                            refresh, local_data=test_entry_2.data)

    def test_db_update_no_remote(self, test_device, test_entry_2, caplog):
        with mock.patch.object(IM.CommandSeq, 'add') as mocked:
            with caplog.at_level(logging.DEBUG):
                two_way = True
                refresh = True
                test_device._db_update(test_entry_2.group,
                                       test_entry_2.is_controller,
                                       test_entry_2.addr,
                                       test_entry_2.group,
                                       two_way,
                                       refresh,
                                       None,
                                       bytes([0x00, 0x00, 0x00]),
                                       test_entry_2.data)
                calls = [call(test_device.db.add_on_device, test_entry_2.addr,
                              test_entry_2.group, test_entry_2.is_controller,
                              bytes([0x00, 0x00, 0x00]))]
                assert mocked.call_count == 1
                call_args = mocked.call_args_list
                assert call_args[0].args[0] == test_device.db.add_on_device
                assert call_args[0].args[1].addr == test_entry_2.addr
                assert call_args[0].args[1].group == test_entry_2.group
                assert call_args[0].args[1].is_controller == test_entry_2.is_controller
                assert call_args[0].args[1].data == bytes([0x00, 0x00, 0x00])
                assert "Modem db add CTRL can't find remote" in caplog.text

    def test_db_add_resp_multigroup(self, test_device, test_device_2, 
                                    test_entry_multigroup):
        test_device.add(test_device_2)
        with mock.patch.object(IM.CommandSeq, 'add') as mocked:
            test_device.db_add_resp_of(0x01,  # local group for responder links on modem is always 0x01
                                       test_device_2.addr,
                                       test_entry_multigroup.group,
                                       False,
                                       False,
                                       local_data=bytes([0x00, 0x00, 0x00]))
            assert mocked.call_count == 1
            call_args = mocked.call_args_list
            assert call_args[0].args[0] == test_device.db.add_on_device
            assert call_args[0].args[1].addr == test_entry_multigroup.addr
            assert call_args[0].args[1].group == test_entry_multigroup.group
            assert call_args[0].args[1].is_controller == False
            assert call_args[0].args[1].data == bytes([0x00, 0x00, 0x00])
