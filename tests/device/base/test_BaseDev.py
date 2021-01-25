#===========================================================================
#
# Tests for: insteont_mqtt/device/Base.py
#
# pylint: disable=W0621,W0212,
#
#===========================================================================
import logging
# from pprint import pprint
from unittest import mock
from unittest.mock import call
import pytest
import insteon_mqtt as IM
from insteon_mqtt.device.base.Base import Base
import insteon_mqtt.message as Msg
import insteon_mqtt.util as util
import helpers as H

@pytest.fixture
def test_device(tmpdir):
    '''
    Returns a generically configured device for testing
    '''
    protocol = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    modem.db = IM.db.Modem(None, modem)
    modem.scenes = IM.Scenes.SceneManager(modem, None)
    addr = IM.Address(0x01, 0x02, 0x03)
    device = Base(protocol, modem, addr)
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
def test_entry_1():
    addr = IM.Address('12.34.ab')
    data = bytes([0xff, 0x00, 0x00])
    group = 0x01
    in_use = True
    is_controller = True
    is_last_rec = False
    db_flags = Msg.DbFlags(in_use, is_controller, is_last_rec)
    mem_loc = 1
    return IM.db.DeviceEntry(addr, group, mem_loc, db_flags, data)

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
        with mock.patch.object(IM.CommandSeq, 'add') as mocked:
            test_device.pair()
            calls = [
                call(test_device.refresh),
            ]
            mocked.assert_has_calls(calls)
            assert mocked.call_count == 1

    def test_broadcast(self, test_device, caplog):
        # test broadcast Messages, Base doesn't handle any
        flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
        group = IM.Address(0x00, 0x00, 0x01)
        addr = IM.Address(0x01, 0x02, 0x03)
        msg = Msg.InpStandard(addr, group, flags, 0x11, 0x00)
        test_device.handle_broadcast(msg)
        assert "has no handler for broadcast" in caplog.text

    def test_join(self, test_device):
        with mock.patch.object(IM.CommandSeq, 'add') as mocked:
            test_device.join()
            calls = [call(test_device.get_engine),
                     call(test_device._join_device)]
            mocked.assert_has_calls(calls, any_order=True)

    def test_join_device(self, test_device):
        test_device.db.engine = 1
        def on_done(success, msg, data):
            assert success
            assert msg == 'Operation Complete.'
        test_device._join_device(on_done=on_done)

        test_device.db.engine = 2
        with mock.patch.object(IM.CommandSeq, 'add') as mocked:
            def fake_link(self):
                pass
            test_device.modem.linking = fake_link
            test_device._join_device()
            calls = [call(test_device.modem.linking),
                     call(test_device.linking)]
            # Must be in this order to get the proper ctrl/resp orientation
            mocked.assert_has_calls(calls, any_order=False)

    def test_device_linking(self, test_device):
        msg = Msg.OutExtended.direct(test_device.addr,
                                     Msg.CmdType.LINKING_MODE, 0x01,
                                     bytes([0x00] * 14))
        test_device.linking()
        sent = test_device.protocol.sent
        assert len(sent) == 1
        assert sent[0].msg.to_bytes() == msg.to_bytes()

    def test_get_flags(self, test_device):
        msg = Msg.OutStandard.direct(test_device.addr,
                                     Msg.CmdType.GET_OPERATING_FLAGS, 0x00)
        test_device.get_flags()
        sent = test_device.protocol.sent
        assert len(sent) == 1
        assert sent[0].msg.to_bytes() == msg.to_bytes()

    def test_get_engine(self, test_device):
        msg = Msg.OutStandard.direct(test_device.addr,
                                     Msg.CmdType.GET_ENGINE_VERSION, 0x00)
        test_device.get_engine()
        sent = test_device.protocol.sent
        assert len(sent) == 1
        assert sent[0].msg.to_bytes().hex() == msg.to_bytes().hex()
        assert isinstance(sent[0].handler, IM.handler.StandardCmdNAK)

    def test_handle_group(self, test_device, caplog):
        with caplog.at_level(logging.DEBUG):
            test_device.handle_group_cmd(None, None)
        assert 'ignoring group cmd - not implemented' in caplog.text

    def test_sync_dry_ref(self, test_device):
        with mock.patch.object(IM.CommandSeq, 'add') as mocked:
            test_device.sync(dry_run=True, refresh=True)
            assert mocked.call_count == 2
            call_args = mocked.call_args_list
            assert call_args[0].args == (test_device.refresh,)
            assert call_args[1].args == (test_device.sync, True)
            assert not call_args[1].kwargs['refresh']

    def test_sync_dry_no_ref(self, test_device, test_entry_1, test_entry_2):
        # Mock up a DB and DB_Config with differences, see if sync properly
        # marks these diffs as needing an update.
        test_device.db.add_entry(test_entry_1)
        test_device.db_config = IM.db.Device(test_device.addr, None,
                                             test_device)
        test_device.db_config.add_entry(test_entry_2)
        with mock.patch.object(IM.CommandSeq, 'add') as mocked:
            test_device.sync(dry_run=True, refresh=False)
            assert mocked.call_count == 2
            call_args = mocked.call_args_list
            assert call_args[0].args == (test_device._sync_del, test_entry_1,
                                         True)
            assert call_args[1].args == (test_device._sync_add, test_entry_2,
                                         True)

    def test_sync_del_dry(self, test_device, test_entry_1):
        def on_done(success, msg, data):
            assert success
        test_device._sync_del(test_entry_1, True, on_done=on_done)

    def test_sync_del(self, test_device, test_entry_1):
        with mock.patch.object(test_device.db, 'delete_on_device') as mocked:
            test_device._sync_del(test_entry_1, False)
            mocked.assert_called_once_with(test_entry_1, on_done=None)

    def test_sync_add_dry(self, test_device, test_entry_1):
        def on_done(success, msg, data):
            assert success
        test_device._sync_add(test_entry_1, True, on_done=on_done)

    def test_sync_add(self, test_device, test_entry_1):
        with mock.patch.object(test_device.db, 'add_on_device') as mocked:
            test_device._sync_add(test_entry_1, False)
            mocked.assert_called_once_with(test_entry_1.addr,
                                           test_entry_1.group,
                                           test_entry_1.is_controller,
                                           test_entry_1.data, on_done=None)

    def test_import_scenes_dry(self, test_device, test_entry_1):
        test_device.db.add_entry(test_entry_1)
        test_device.db_config = IM.db.Device(test_device.addr, None,
                                             test_device)
        test_device.import_scenes()
        # Dry Run, nothing changed
        assert test_device.modem.scenes.data == []

    def test_import_scenes(self, test_device, test_entry_1):
        test_device.db.add_entry(test_entry_1)
        test_device.db_config = IM.db.Device(test_device.addr, None,
                                             test_device)
        test_device.import_scenes(dry_run=False)
        # Dry Run, nothing changed
        assert test_device.modem.scenes.data == [{'controllers':
                                                  [{'01.02.03':
                                                        {'data_1': 255,
                                                         'data_3': 0}}],
                                                  'responders':
                                                  ['12.34.ab']}]

    def test_import_scenes_none(self, test_device, test_entry_1):
        test_device.db_config = IM.db.Device(test_device.addr, None,
                                             test_device)
        test_device.import_scenes(dry_run=False)
        # Dry Run, nothing changed
        assert test_device.modem.scenes.data == []

    def test_db_add_ctrl(self, test_device):
        with mock.patch.object(test_device, '_db_update') as mocked:
            local_group = 0x01
            remote_addr = IM.Address('01.02.03')
            remote_group = 0x01
            test_device.db_add_ctrl_of(local_group, remote_addr, remote_group)
        mocked.assert_called_once_with(local_group, True, remote_addr,
                                       remote_group, True,
                                       True, None,
                                       None, None)

    def test_db_add_resp(self, test_device):
        with mock.patch.object(test_device, '_db_update') as mocked:
            local_group = 0x01
            remote_addr = IM.Address('01.02.03')
            remote_group = 0x01
            test_device.db_add_resp_of(local_group, remote_addr, remote_group)
        mocked.assert_called_once_with(local_group, False, remote_addr,
                                       remote_group, True,
                                       True, None,
                                       None, None)

    def test_db_del_ctrl(self, test_device):
        with mock.patch.object(test_device, '_db_delete') as mocked:
            group = 0x01
            addr = IM.Address('01.02.03')
            test_device.db_del_ctrl_of(addr, group)
            mocked.assert_called_once_with(addr, group, True, True,
                                           True, None)

    def test_db_del_resp(self, test_device):
        with mock.patch.object(test_device, '_db_delete') as mocked:
            group = 0x01
            addr = IM.Address('01.02.03')
            test_device.db_del_resp_of(addr, group)
            mocked.assert_called_once_with(addr, group, False, True,
                                           True, None)

    def test_run_cmd_empty(self, test_device, caplog):
        test_device.run_command()
        assert 'Invalid command sent to device' in caplog.text

    def test_run_cmd_bad_cmd(self, test_device, caplog):
        test_device.run_command(cmd="NoSuchThing")
        assert 'Invalid command sent to device' in caplog.text

    def test_run_cmd_missing_arg(self, test_device, caplog):
        test_device.run_command(cmd='print_db')
        assert 'Invalid command inputs to device' in caplog.text

    def test_run_cmd_good(self, test_device, caplog):
        def on_done(success, msg, data):
            assert success
        test_device.run_command(cmd='print_db', on_done=on_done)

    def test_handle_flags(self, test_device, caplog):
        def on_done(success, msg, data):
            assert success
            assert msg == "Operation complete"
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, False)
        group = IM.Address(0x00, 0x00, 0x01)
        addr = IM.Address(0x01, 0x02, 0x03)
        msg = Msg.InpStandard(addr, group, flags,
                              Msg.CmdType.GET_OPERATING_FLAGS, 0x55)
        with caplog.at_level(logging.DEBUG):
            test_device.handle_flags(msg, on_done=on_done)
            assert 'operating flags: 01010101' in caplog.text

    def test_handle_engine_nak(self, test_device, caplog):
        def on_done(success, msg, data):
            assert success
            assert msg == "Operation complete"
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_NAK, False)
        group = IM.Address(0x00, 0x00, 0x01)
        addr = IM.Address(0x01, 0x02, 0x03)
        msg = Msg.InpStandard(addr, group, flags,
                              Msg.CmdType.GET_ENGINE_VERSION, 0x00)
        with caplog.at_level(logging.DEBUG):
            test_device.handle_engine(msg, on_done=on_done)
            assert 'sent NAK to get engine' in caplog.text
            assert test_device.db.engine == 2

    def test_handle_model(self, test_device, caplog):
        def on_done(success, msg, data):
            assert success
            assert msg == "Operation complete"
        flags = Msg.Flags(Msg.Flags.Type.BROADCAST, False)
        to_addr = IM.Address(0x01, 0x30, 0x45)
        from_addr = IM.Address(0x01, 0x02, 0x03)
        msg = Msg.InpStandard(from_addr, to_addr, flags, 0x01, 0x00)
        with caplog.at_level(logging.DEBUG):
            test_device.handle_model(msg, on_done=on_done)
            assert 'received model information' in caplog.text
            assert '2476D' in test_device.db.desc.model

    def test_handle_model_bad_resp(self, test_device, caplog):
        def on_done(success, msg, data):
            assert not success
            assert "Operation failed" in msg
        flags = Msg.Flags(Msg.Flags.Type.BROADCAST, False)
        to_addr = IM.Address(0x01, 0x30, 0x45)
        from_addr = IM.Address(0x01, 0x02, 0x03)
        msg = Msg.InpStandard(from_addr, to_addr, flags, 0x05, 0x00)
        with caplog.at_level(logging.DEBUG):
            test_device.handle_model(msg, on_done=on_done)
            assert 'get_model response with wrong cmd' in caplog.text

    def test_update_linked_devices(self, test_device, test_entry_1,
                                   test_entry_2, test_device_2, caplog):
        test_device.db.add_entry(test_entry_1)
        test_device.db.add_entry(test_entry_2)
        test_device.modem.add(test_device_2)
        test_device.db_config = IM.db.Device(test_device.addr, None,
                                             test_device)
        flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
        group = IM.Address(0x00, 0x00, 0x01)
        addr = IM.Address(0x01, 0x02, 0x03)
        msg = Msg.InpStandard(addr, group, flags, 0x11, 0x00)
        with caplog.at_level(logging.DEBUG):
            test_device.update_linked_devices(msg)
            assert 'device 12.34.ab is not in config' in caplog.text
            assert 'Device 56.78.cd ignoring group cmd' in caplog.text

    def test_db_update(self, test_device, test_entry_2,
                       test_device_2, caplog):
        test_device.modem.add(test_device_2)
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
                assert mocked.call_count == 3
                calls = [call(test_device.refresh),
                         call(test_device.db.add_on_device, test_entry_2.addr,
                              test_entry_2.group, test_entry_2.is_controller,
                              bytes([0x00, 0x00, 0x00])),
                         call(test_device_2.db_add_resp_of, test_entry_2.group,
                              test_device.addr, test_entry_2.group, False,
                              refresh, local_data=test_entry_2.data)]
                mocked.assert_has_calls(calls)

    def test_db_update_resp(self, test_device, test_entry_2,
                            test_device_2, caplog):
        test_device.modem.add(test_device_2)
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
                assert mocked.call_count == 3
                calls = [call(test_device.refresh),
                         call(test_device.db.add_on_device, test_entry_2.addr,
                              test_entry_2.group, False,
                              bytes([0x00, 0x00, 0x00])),
                         call(test_device_2.db_add_ctrl_of, test_entry_2.group,
                              test_device.addr, test_entry_2.group, False,
                              refresh, local_data=test_entry_2.data)]
                mocked.assert_has_calls(calls)

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
                calls = [call(test_device.refresh),
                         call(test_device.db.add_on_device, test_entry_2.addr,
                              test_entry_2.group, test_entry_2.is_controller,
                              bytes([0x00, 0x00, 0x00]))]
                assert mocked.call_count == 2
                mocked.assert_has_calls(calls)
                assert "Device db add CTRL can't find remote" in caplog.text

    def test_db_delete_no_remote_no_entry(self, test_device, test_entry_2,
                                          caplog):
        def on_done(success, msg, data):
            assert not success
        with mock.patch.object(IM.CommandSeq, 'add') as mocked:
            with caplog.at_level(logging.DEBUG):
                two_way = True
                refresh = True
                test_device._db_delete(test_entry_2.addr,
                                       test_entry_2.group,
                                       test_entry_2.is_controller,
                                       two_way,
                                       refresh,
                                       on_done)
                assert mocked.call_count == 0
                assert "delete no match for 56.78.cd grp 1 CTRL" in caplog.text
