#===========================================================================
#
# Tests for: insteont_mqtt/db/DeviceEntry.py
#
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_DeviceEntry:
    #-----------------------------------------------------------------------
    def test_ctrl(self):
        addr = IM.Address('12.34.ab')
        ctrl = Msg.DbFlags(in_use=True, is_controller=True, is_last_rec=False)
        data = bytes([0x01, 0x02, 0x03])
        mem_loc = (0xfe << 8) + 0x10
        obj = IM.db.DeviceEntry(addr, 0x03, mem_loc, ctrl, data, db=None)

        assert obj.addr == addr
        assert obj.group == 0x03
        assert obj.db_flags.in_use == ctrl.in_use
        assert obj.db_flags.is_controller == ctrl.is_controller
        assert obj.db_flags.is_last_rec == ctrl.is_last_rec
        assert obj.mem_loc == mem_loc
        assert obj.data == data
        assert obj.mem_bytes() == bytes([0xfe, 0x10])

        d = obj.to_json()
        obj2 = IM.db.DeviceEntry.from_json(d, db=None)
        assert obj2.addr == obj.addr
        assert obj2.group == obj.group
        assert obj2.mem_loc == obj.mem_loc
        assert obj2.db_flags.in_use == obj.db_flags.in_use
        assert obj2.db_flags.is_controller == obj.db_flags.is_controller
        assert obj2.db_flags.is_last_rec == obj.db_flags.is_last_rec
        assert obj2.data == obj.data
        assert obj == obj2

        data = bytes([0x00, 0x01,
                      0xfe, 0x10,  # mem_loc
                      0x00, ctrl.to_bytes()[0], 0x03,
                      addr.ids[0], addr.ids[1], addr.ids[2],
                      data[0], data[1], data[2]])

        obj3 = IM.db.DeviceEntry.from_bytes(data, db=None)
        assert obj3.addr == obj.addr
        assert obj3.group == obj.group
        assert obj3.mem_loc == obj.mem_loc
        assert obj3.db_flags.in_use == obj.db_flags.in_use
        assert obj3.db_flags.is_controller == obj.db_flags.is_controller
        assert obj3.db_flags.is_last_rec == obj.db_flags.is_last_rec
        assert obj3.data == obj.data
        assert obj == obj3

        obj3.group = 0xff
        assert obj != obj3
        assert obj < obj3

        obj.addr = IM.Address('12.34.ac')
        assert obj3 < obj

        str(obj)

    #-----------------------------------------------------------------------
    def test_label(self):
        addr = IM.Address('12.34.ab')
        ctrl = Msg.DbFlags(in_use=True, is_controller=True, is_last_rec=False)
        data = bytes([0x01, 0x02, 0x03])
        mem_loc = (0xfe << 8) + 0x10
        obj = IM.db.DeviceEntry(addr, 0x03, mem_loc, ctrl, data, db=None)

        assert obj.label == str(addr)

        protocol = MockProto()
        modem = MockModem()
        addr1 = IM.Address(0x03, 0x04, 0x05)
        addr = IM.Address('12.34.ab')
        device1 = IM.device.Base(protocol, modem, addr1)
        obj = IM.db.DeviceEntry(addr, 0x03, mem_loc, ctrl, data, db=device1.db)
        device = IM.device.Base(protocol, modem, addr, name="Awesomesauce")
        modem.set_linked_device(device)

        assert obj.label == "12.34.ab (Awesomesauce)"

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
