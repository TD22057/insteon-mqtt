#===========================================================================
#
# Tests for: insteont_mqtt/handler/ModemDbSearch.py
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

class Test_ModemDbModify:
    def test_ack(self, test_db, test_entry_dev1_ctrl):
        handler = Handler.ModemDbSearch(test_db)
        db_flags = Msg.DbFlags(in_use=True,
                               is_controller=test_entry_dev1_ctrl.is_controller,
                               is_last_rec=False)
        msg = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.EXISTS,
                                   db_flags,
                                   test_entry_dev1_ctrl.group,
                                   test_entry_dev1_ctrl.addr,
                                   data=None, is_ack=True)
        ret = handler.msg_received(test_db.device.protocol, msg)
        assert ret == Msg.CONTINUE

    def test_nack(self, test_db, test_entry_dev1_ctrl):
        handler = Handler.ModemDbSearch(test_db)
        db_flags = Msg.DbFlags(in_use=True,
                               is_controller=test_entry_dev1_ctrl.is_controller,
                               is_last_rec=False)
        msg = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.EXISTS,
                                   db_flags,
                                   test_entry_dev1_ctrl.group,
                                   test_entry_dev1_ctrl.addr,
                                   data=None, is_ack=False)
        ret = handler.msg_received(test_db.device.protocol, msg)
        assert ret == Msg.FINISHED

    def test_wrong_handler(self, test_db, test_entry_dev1_ctrl):
        handler = Handler.ModemDbSearch(test_db)
        msg = Msg.OutAllLinkCancel()
        ret = handler.msg_received(test_db.device.protocol, msg)
        assert ret == Msg.UNKNOWN

    def test_entry_received(self, test_db, test_entry_dev1_ctrl):
        handler = Handler.ModemDbSearch(test_db)
        db_flags = Msg.DbFlags(in_use=True,
                               is_controller=test_entry_dev1_ctrl.is_controller,
                               is_last_rec=False)
        msg = Msg.InpAllLinkRec(db_flags, test_entry_dev1_ctrl.group,
                                test_entry_dev1_ctrl.addr,
                                test_entry_dev1_ctrl.data)
        ret = handler.msg_received(test_db.device.protocol, msg)
        assert ret == Msg.FINISHED
        assert len(test_db) == 1
        assert test_db.entries[0] == test_entry_dev1_ctrl
        sent = test_db.device.protocol.sent
        assert len(sent) == 1
        assert sent[0].msg.cmd == Msg.OutAllLinkUpdate.Cmd.SEARCH
        assert sent[0].msg.group == test_entry_dev1_ctrl.group
        assert sent[0].msg.addr == test_entry_dev1_ctrl.addr

    def test_entry_not_used(self, test_db, test_entry_dev1_ctrl):
        # I don't think this is possible, but we have the code, so test for it
        handler = Handler.ModemDbSearch(test_db)
        db_flags = Msg.DbFlags(in_use=False,
                               is_controller=test_entry_dev1_ctrl.is_controller,
                               is_last_rec=False)
        msg = Msg.InpAllLinkRec(db_flags, test_entry_dev1_ctrl.group,
                                test_entry_dev1_ctrl.addr,
                                test_entry_dev1_ctrl.data)
        ret = handler.msg_received(test_db.device.protocol, msg)
        assert ret == Msg.FINISHED
        assert len(test_db) == 0
        sent = test_db.device.protocol.sent
        assert len(sent) == 1
        assert sent[0].msg.cmd == Msg.OutAllLinkUpdate.Cmd.SEARCH
        assert sent[0].msg.group == test_entry_dev1_ctrl.group
        assert sent[0].msg.addr == test_entry_dev1_ctrl.addr
