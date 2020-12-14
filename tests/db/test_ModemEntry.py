#===========================================================================
#
# Tests for: insteont_mqtt/db/ModemEntry.py
#
#===========================================================================
import insteon_mqtt as IM


class Test_ModemEntry:
    #-----------------------------------------------------------------------
    def test_ctrl(self):
        addr = IM.Address('12.34.ab')
        data = bytes([0x01, 0x02, 0x03])
        obj = IM.db.ModemEntry(addr, 0x03, True, data, db=None)

        assert obj.addr == addr
        assert obj.group == 0x03
        assert obj.is_controller is True
        assert obj.data == data

        d = obj.to_json()
        obj2 = IM.db.ModemEntry.from_json(d, db=None)
        assert obj2.addr == obj.addr
        assert obj2.group == obj.group
        assert obj2.is_controller == obj.is_controller
        assert obj2.data == obj.data

        assert obj2 == obj
        obj2.group = 0x01
        assert obj2 != obj

        str(obj)

        # compare w/ groups
        obj2.group = 0x02
        assert obj2 < obj

        # compare w/ addr
        obj2.addr = IM.Address('12.34.ac')
        assert obj < obj2

    #-----------------------------------------------------------------------
    def test_resp(self):
        addr = IM.Address('12.34.ab')
        data = bytes([0x01, 0x02, 0x03])
        obj = IM.db.ModemEntry(addr, 0x03, False, data, db=None)

        assert obj.addr == addr
        assert obj.group == 0x03
        assert obj.is_controller is False
        assert obj.data == data

        d = obj.to_json()
        obj2 = IM.db.ModemEntry.from_json(d, db=None)
        assert obj2.addr == obj.addr
        assert obj2.group == obj.group
        assert obj2.is_controller == obj.is_controller
        assert obj2.data == obj.data

        assert obj2 == obj
        obj2.group = 0x01
        assert obj2 != obj

        str(obj)

    #-----------------------------------------------------------------------
    def test_label(self):
        addr = IM.Address('12.34.ab')
        data = bytes([0x01, 0x02, 0x03])
        obj = IM.db.ModemEntry(addr, 0x03, False, data, db=None)

        assert obj.label == str(addr)

        protocol = MockProto()
        modem = MockModem()
        db = MockDB(modem)
        addr = IM.Address(0x03, 0x04, 0x05)
        obj = IM.db.ModemEntry(addr, 0x03, False, data, db=db)
        device = IM.device.Base(protocol, modem, addr, name="Awesomesauce")
        modem.set_linked_device(device)

        assert obj.label == "03.04.05 (Awesomesauce)"

    #-----------------------------------------------------------------------


#===========================================================================
class MockProto:
    def __init__(self):
        self.msgs = []

    def send(self, msg, handler, high_priority=False, after=None):
        self.msgs.append(msg)

class MockModem():
    def __init__(self):
        self.save_path = ''
        self.linked_device = None

    def set_linked_device(self, device):
        self.linked_device = device

    def find(self, *args, **kwargs):
        return self.linked_device

class MockDB():
    def __init__(self, modem):
        self.device = modem
