#===========================================================================
#
# Tests for: insteont_mqtt/handler/ModemDbModify.py
#
# pylint: disable=W0621
#===========================================================================
# from unittest import mock
# from unittest.mock import call
import pytest
import insteon_mqtt as IM
import insteon_mqtt.handler as Handler
import insteon_mqtt.message as Msg
import helpers as H

@pytest.fixture
def test_db(tmpdir):
    #modem_db, entry, existing_entry=None
    path = tmpdir.join("temp.json")
    protocol = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    addr = IM.Address(0x01, 0x02, 0x03)
    device = H.main.MockDevice(protocol, modem, addr)
    modem.db = IM.db.Modem(path=path, device=device)
    return modem.db

@pytest.fixture
def test_entry_dev1_ctrl():
    addr = IM.Address('12.34.ab')
    data = bytes([0xff, 0x00, 0x00])
    group = 0x01
    is_controller = True
    return IM.db.ModemEntry(addr, group, is_controller, data)

@pytest.fixture
def test_entry_dev1_ctrl_mod():
    addr = IM.Address('12.34.ab')
    data = bytes([0x12, 0x34, 0x56])
    group = 0x01
    is_controller = True
    return IM.db.ModemEntry(addr, group, is_controller, data)

@pytest.fixture
def test_entry_dev1_resp():
    addr = IM.Address('12.34.ab')
    data = bytes([0xff, 0x00, 0x00])
    group = 0x01
    is_controller = False
    return IM.db.ModemEntry(addr, group, is_controller, data)

@pytest.fixture
def test_entry_dev2_ctrl():
    addr = IM.Address('12.34.ab')
    data = bytes([0xff, 0x00, 0x00])
    group = 0x01
    is_controller = False
    return IM.db.ModemEntry(addr, group, is_controller, data)

class Test_ModemDbModify:
    def test_delete(self, test_db, test_entry_dev1_ctrl):
        # delete, no next
        test_db.add_entry(test_entry_dev1_ctrl)
        assert len(test_db) == 1
        handler = Handler.ModemDbModify(test_db, test_entry_dev1_ctrl)
        db_flags = Msg.DbFlags(in_use=True,
                               is_controller=test_entry_dev1_ctrl.is_controller,
                               is_last_rec=False)
        msg = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.DELETE,
                                   db_flags,
                                   test_entry_dev1_ctrl.group,
                                   test_entry_dev1_ctrl.addr,
                                   data=None, is_ack=True)
        handler.msg_received(test_db.device.protocol, msg)
        assert len(test_db) == 0

    def test_delete2(self, test_db, test_entry_dev1_ctrl,
                     test_entry_dev1_resp):
        # delete 2nd entry and then re-add the first
        test_db.add_entry(test_entry_dev1_ctrl)
        test_db.add_entry(test_entry_dev1_resp)
        assert len(test_db) == 2
        handler = Handler.ModemDbModify(test_db, test_entry_dev1_ctrl)
        db_flags = Msg.DbFlags(in_use=True,
                               is_controller=test_entry_dev1_ctrl.is_controller,
                               is_last_rec=False)
        msg = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.DELETE,
                                   db_flags,
                                   test_entry_dev1_ctrl.group,
                                   test_entry_dev1_ctrl.addr,
                                   data=None)
        # Add update to delete 2nd entry
        handler.add_update(msg, test_entry_dev1_resp)
        # Then restore the first
        db_flags = Msg.DbFlags(in_use=True,
                               is_controller=test_entry_dev1_ctrl.is_controller,
                               is_last_rec=False)
        msg2 = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.ADD_CONTROLLER,
                                    db_flags, test_entry_dev1_ctrl.group,
                                    test_entry_dev1_ctrl.addr,
                                    test_entry_dev1_ctrl.data)
        handler.add_update(msg2, test_entry_dev1_ctrl)
        # signal first delete ack
        msg.is_ack = True
        handler.msg_received(test_db.device.protocol, msg)
        assert len(test_db) == 1
        # signal second delete ack
        handler.msg_received(test_db.device.protocol, msg)
        assert len(test_db) == 0
        # signal final add ack
        msg2.is_ack = True
        handler.msg_received(test_db.device.protocol, msg2)
        assert len(test_db) == 1
        assert test_db.entries[0] == test_entry_dev1_ctrl

    def test_delete_nak(self, test_db, test_entry_dev1_ctrl, caplog):
        # delete, no next
        test_db.add_entry(test_entry_dev1_ctrl)
        assert len(test_db) == 1
        handler = Handler.ModemDbModify(test_db, test_entry_dev1_ctrl)
        db_flags = Msg.DbFlags(in_use=True,
                               is_controller=test_entry_dev1_ctrl.is_controller,
                               is_last_rec=False)
        msg = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.DELETE,
                                   db_flags,
                                   test_entry_dev1_ctrl.group,
                                   test_entry_dev1_ctrl.addr,
                                   data=None, is_ack=False)
        handler.msg_received(test_db.device.protocol, msg)
        assert len(test_db) == 1
        assert "db update failed" in caplog.text

    def test_update(self, test_db, test_entry_dev1_ctrl,
                    test_entry_dev1_ctrl_mod):
        # update clean
        test_db.add_entry(test_entry_dev1_ctrl)
        assert len(test_db) == 1
        handler = Handler.ModemDbModify(test_db, test_entry_dev1_ctrl_mod,
                                        existing_entry=test_entry_dev1_ctrl)
        db_flags = Msg.DbFlags(in_use=True,
                               is_controller=test_entry_dev1_ctrl.is_controller,
                               is_last_rec=False)
        msg = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.UPDATE,
                                   db_flags,
                                   test_entry_dev1_ctrl.group,
                                   test_entry_dev1_ctrl.addr,
                                   data=bytes(3), is_ack=True)
        handler.msg_received(test_db.device.protocol, msg)
        assert len(test_db) == 1
        assert test_db.entries[0].data == test_entry_dev1_ctrl_mod.data

    def test_add(self, test_db, test_entry_dev1_ctrl):
        # add clean
        assert len(test_db) == 0
        handler = Handler.ModemDbModify(test_db, test_entry_dev1_ctrl)
        db_flags = Msg.DbFlags(in_use=True,
                               is_controller=test_entry_dev1_ctrl.is_controller,
                               is_last_rec=False)
        msg = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.ADD_CONTROLLER,
                                   db_flags,
                                   test_entry_dev1_ctrl.group,
                                   test_entry_dev1_ctrl.addr,
                                   data=bytes(3), is_ack=True)
        handler.msg_received(test_db.device.protocol, msg)
        assert len(test_db) == 1
        assert test_db.entries[0] == test_entry_dev1_ctrl

    def test_add_nak(self, test_db, test_entry_dev1_ctrl):
        assert len(test_db) == 0
        handler = Handler.ModemDbModify(test_db, test_entry_dev1_ctrl)
        db_flags = Msg.DbFlags(in_use=True,
                               is_controller=test_entry_dev1_ctrl.is_controller,
                               is_last_rec=False)
        msg = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.ADD_CONTROLLER,
                                   db_flags,
                                   test_entry_dev1_ctrl.group,
                                   test_entry_dev1_ctrl.addr,
                                   data=bytes(3), is_ack=False)
        handler.msg_received(test_db.device.protocol, msg)
        # entry should be added
        assert len(test_db) == 1
        assert len(test_db.device.protocol.sent) == 1
        assert (test_db.device.protocol.sent[0].msg.cmd ==
                Msg.OutAllLinkUpdate.Cmd.UPDATE)
        assert handler.is_retry

    def test_update_nak(self, test_db, test_entry_dev1_ctrl,
                        test_entry_dev1_ctrl_mod):
        test_db.add_entry(test_entry_dev1_ctrl)
        assert len(test_db) == 1
        handler = Handler.ModemDbModify(test_db, test_entry_dev1_ctrl_mod,
                                        existing_entry=test_entry_dev1_ctrl)
        db_flags = Msg.DbFlags(in_use=True,
                               is_controller=test_entry_dev1_ctrl.is_controller,
                               is_last_rec=False)
        msg = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.UPDATE,
                                   db_flags,
                                   test_entry_dev1_ctrl_mod.group,
                                   test_entry_dev1_ctrl_mod.addr,
                                   data=bytes(3), is_ack=False)
        handler.msg_received(test_db.device.protocol, msg)
        # entry should still be there, it gets updated on next ack
        assert len(test_db) == 1
        assert len(test_db.device.protocol.sent) == 1
        assert (test_db.device.protocol.sent[0].msg.cmd ==
                Msg.OutAllLinkUpdate.Cmd.ADD_CONTROLLER)
        assert handler.is_retry

    def test_prevent_loop(self, test_db, test_entry_dev1_ctrl, caplog):
        handler = Handler.ModemDbModify(test_db, test_entry_dev1_ctrl_mod,
                                        existing_entry=test_entry_dev1_ctrl)
        handler.is_retry = True
        db_flags = Msg.DbFlags(in_use=True,
                               is_controller=test_entry_dev1_ctrl.is_controller,
                               is_last_rec=False)
        msg = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.UPDATE,
                                   db_flags,
                                   test_entry_dev1_ctrl.group,
                                   test_entry_dev1_ctrl.addr,
                                   data=bytes(3), is_ack=False)
        handler.msg_received(test_db.device.protocol, msg)
        # This should fail to prevent infinite loops
        assert "db update failed" in caplog.text

    def test_wrong_handler(self, test_db, test_entry_dev1_ctrl):
        handler = Handler.ModemDbModify(test_db, test_entry_dev1_ctrl_mod,
                                        existing_entry=test_entry_dev1_ctrl)
        msg = Msg.OutAllLinkCancel()
        ret = handler.msg_received(test_db.device.protocol, msg)
        # This should fail to prevent infinite loops
        assert ret == Msg.UNKNOWN
