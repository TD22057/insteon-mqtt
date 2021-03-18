#===========================================================================
#
# Tests for: insteont_mqtt/db/Modem.py
#
# pylint: disable=W0621,W0212
#===========================================================================
from unittest import mock
from unittest.mock import call
import pytest
import insteon_mqtt as IM
import insteon_mqtt.message as Msg
import helpers as H


@pytest.fixture
def test_device(tmpdir):
    path = tmpdir.join("temp.json")
    protocol = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    addr = IM.Address(0x01, 0x02, 0x03)
    device = H.main.MockDevice(protocol, modem, addr)
    return IM.db.Modem(path=path, device=device)

@pytest.fixture
def test_entry_dev1_ctrl():
    addr = IM.Address('12.34.ab')
    data = bytes([0xff, 0x00, 0x00])
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

class Test_Modem:
    #-----------------------------------------------------------------------
    def test_basic(self):
        obj = IM.db.Modem()
        assert len(obj) == 0

        addr = IM.Address('12.34.ab')
        data = bytes([0xff, 0x00, 0x00])
        e = IM.db.ModemEntry(addr, 0x01, True, data, db=obj)
        obj.add_entry(e)

        addr = IM.Address('12.34.ac')
        data = bytes([0xff, 0x00, 0x00])
        e = IM.db.ModemEntry(addr, 0x01, True, data, db=obj)
        obj.add_entry(e)

        addr = IM.Address('12.34.ad')
        data = bytes([0xff, 0x00, 0x00])
        e = IM.db.ModemEntry(addr, 0x02, True, data, db=obj)
        obj.add_entry(e)

        assert len(obj) == 3
        str(obj)

        j = obj.to_json()
        obj2 = IM.db.Modem.from_json(j)

        assert len(obj2) == 3
        assert obj2.entries[0] == obj.entries[0]
        assert obj2.entries[1] == obj.entries[1]
        assert obj2.entries[2] == obj.entries[2]

    #-----------------------------------------------------------------------
    def test_clear(self):
        obj = IM.db.Modem()
        assert len(obj) == 0

        addr = IM.Address('12.34.ab')
        data = bytes([0xff, 0x00, 0x00])
        e = IM.db.ModemEntry(addr, 0x01, True, data, db=obj)
        obj.add_entry(e)

        addr = IM.Address('12.34.ac')
        data = bytes([0xff, 0x00, 0x00])
        e = IM.db.ModemEntry(addr, 0x01, True, data, db=obj)
        obj.add_entry(e)

        addr = IM.Address('12.34.ad')
        data = bytes([0xff, 0x00, 0x00])
        e = IM.db.ModemEntry(addr, 0x02, True, data, db=obj)
        obj.add_entry(e)

        assert len(obj) == 3

        obj.set_meta('test', 2)
        obj.clear()
        assert len(obj) == 0
        assert len(obj.entries) == 0
        assert len(obj.groups) == 0
        assert len(obj.aliases) == 0
        assert len(obj._meta) == 1
        assert obj.get_meta('test') == 2

    #-----------------------------------------------------------------------
    def test_add_on_device_empty_ctrl(self, test_device, test_entry_dev1_ctrl):
        # add_on_device(self, entry, on_done=None)
        # test adding to an entry db with ctrl
        assert len(test_device) == 0
        test_device.add_on_device(test_entry_dev1_ctrl)
        assert (test_device.device.protocol.sent[0].msg.cmd ==
                Msg.OutAllLinkUpdate.Cmd.ADD_CONTROLLER)
        assert (test_device.device.protocol.sent[0].msg.db_flags.to_bytes() ==
                Msg.DbFlags(in_use=True, is_controller=True,
                            is_last_rec=False).to_bytes())

    #-----------------------------------------------------------------------
    def test_add_on_device_empty_resp(self, test_device, test_entry_dev1_resp):
        # add_on_device(self, entry, on_done=None)
        # test adding a resp to an empty db
        assert len(test_device) == 0
        test_device.add_on_device(test_entry_dev1_resp)
        assert (test_device.device.protocol.sent[0].msg.cmd ==
                Msg.OutAllLinkUpdate.Cmd.ADD_RESPONDER)
        assert (test_device.device.protocol.sent[0].msg.db_flags.to_bytes() ==
                Msg.DbFlags(in_use=True, is_controller=False,
                            is_last_rec=False).to_bytes())

    #-----------------------------------------------------------------------
    def test_add_on_device_update_resp(self, test_device,
                                       test_entry_dev1_resp):
        # add_on_device(self, entry, on_done=None)
        # test calling update on an existing entry
        test_device.add_entry(test_entry_dev1_resp)
        test_device.add_on_device(test_entry_dev1_resp)
        assert (test_device.device.protocol.sent[0].msg.cmd ==
                Msg.OutAllLinkUpdate.Cmd.UPDATE)
        assert (test_device.device.protocol.sent[0].msg.db_flags.to_bytes() ==
                Msg.DbFlags(in_use=True, is_controller=False,
                            is_last_rec=False).to_bytes())

    #-----------------------------------------------------------------------
    def test_delete_on_device_update_resp(self, test_device,
                                          test_entry_dev1_resp,
                                          test_entry_dev1_ctrl):
        # test calling delete
        test_device.add_entry(test_entry_dev1_resp)
        test_device.add_entry(test_entry_dev1_ctrl)
        test_device.delete_on_device(test_entry_dev1_resp)
        test_device.delete_on_device(test_entry_dev1_ctrl)
        assert (test_device.device.protocol.sent[0].msg.cmd ==
                Msg.OutAllLinkUpdate.Cmd.DELETE)
        assert (test_device.device.protocol.sent[0].msg.db_flags.to_bytes() ==
                Msg.DbFlags(in_use=True, is_controller=False,
                            is_last_rec=False).to_bytes())
        assert (test_device.device.protocol.sent[0].msg.addr ==
                test_entry_dev1_resp.addr)
        assert (test_device.device.protocol.sent[0].msg.group ==
                test_entry_dev1_resp.group)
        assert (test_device.device.protocol.sent[1].msg.cmd ==
                Msg.OutAllLinkUpdate.Cmd.DELETE)
        assert (test_device.device.protocol.sent[1].msg.db_flags.to_bytes() ==
                Msg.DbFlags(in_use=True, is_controller=True,
                            is_last_rec=False).to_bytes())


    #-----------------------------------------------------------------------
