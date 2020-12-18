#===========================================================================
#
# Tests for: insteont_mqtt/db/Device.py
#
# pylint: disable=too-many-statements
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg
import helpers as H

class Test_Device:
    #-----------------------------------------------------------------------
    def test_basic(self):
        obj = IM.db.Device(IM.Address(0x01, 0x02, 0x03))
        assert len(obj) == 0

        assert obj.is_current(0) is False
        obj.delta = 1
        assert obj.is_current(1) is True
        obj.set_delta(None)
        assert obj.is_current(1) is False

        assert obj.engine is None
        obj.set_engine(1)
        assert obj.engine == 1

        assert obj.desc is None
        assert obj.firmware is None
        obj.set_info(1, 2, 3)
        assert obj.desc.dev_cat == 1
        assert obj.desc.sub_cat == 2
        assert obj.firmware == 3

        addr = IM.Address(0x10, 0xab, 0x1c)
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)
        db_flags = Msg.DbFlags(in_use=True, is_controller=True,
                               is_last_rec=False)
        data = bytes([0x01, 0x02, 0x03])
        raw = [0x00, 0x01,
               0xfe, 0x10,  # mem_loc
               0x00, db_flags.to_bytes()[0],
               0x03,  # group
               addr.ids[0], addr.ids[1], addr.ids[2],
               data[0], data[1], data[2], 0x06]
        msg = Msg.InpExtended(addr, addr, flags, 0x00, 0x00, bytes(raw))
        entry = IM.db.DeviceEntry.from_bytes(msg.data, db=obj)
        obj.add_entry(entry)

        # add same addr w/ different group
        raw[6] = 0x02
        raw[3] = 0x11  # have to change memory location
        msg.data = raw
        entry = IM.db.DeviceEntry.from_bytes(msg.data, db=obj)
        obj.add_entry(entry)

        # new addr, same group
        addr2 = IM.Address(0x10, 0xab, 0x1d)
        raw[9] = 0x1d
        raw[3] = 0x12  # have to change memory location
        msg.data = raw
        entry = IM.db.DeviceEntry.from_bytes(msg.data, db=obj)
        obj.add_entry(entry)

        # responder - not in a group
        db_flags = Msg.DbFlags(in_use=True, is_controller=False,
                               is_last_rec=False)
        raw[5] = db_flags.to_bytes()[0]
        raw[3] = 0x13  # have to change memory location
        msg.data = raw
        entry = IM.db.DeviceEntry.from_bytes(msg.data, db=obj)
        obj.add_entry(entry)

        # in use = False
        db_flags = Msg.DbFlags(in_use=False, is_controller=True,
                               is_last_rec=False)
        raw[5] = db_flags.to_bytes()[0]
        raw[3] = 0x14  # have to change memory location
        msg.data = raw
        entry = IM.db.DeviceEntry.from_bytes(msg.data, db=obj)
        obj.add_entry(entry)

        assert len(obj.entries) == 4
        assert len(obj.unused) == 1
        assert len(obj.groups) == 2

        grp = obj.find_group(0x02)
        assert len(grp) == 2
        assert grp[0].addr == addr
        assert grp[1].addr == addr2

        e = obj.find(addr, 0x02, True)
        assert e.addr == addr
        assert e.group == 0x02
        assert e.db_flags.is_controller is True

        e = obj.find(addr2, 0x02, False)
        assert e.addr == addr2
        assert e.group == 0x02
        assert e.db_flags.is_controller is False

        e = obj.find(addr, 0x05, False)
        assert e is None

        str(obj)

        j = obj.to_json()
        obj2 = IM.db.Device.from_json(j, '', None)
        assert len(obj2.entries) == 4
        assert len(obj2.unused) == 1
        assert len(obj2.groups) == 2

        obj2.clear()
        assert len(obj2) == 0
        assert len(obj2.entries) == 0
        assert len(obj2.unused) == 0
        assert len(obj2.groups) == 0

    #-----------------------------------------------------------------------
    def test_add_multi_group(self):
        device = MockDevice()

        local_addr = IM.Address(0x01, 0x02, 0x03)
        db = IM.db.Device(local_addr, device=device)

        # Add local group 1 as responder of scene 30 on remote.
        data = bytes([0xff, 0x00, 0x01])
        is_controller = False
        remote_addr = IM.Address(0x50, 0x51, 0x52)
        remote_group = 0x30

        db.add_on_device(remote_addr, remote_group, is_controller, data)
        assert len(device.sent) == 2
        assert len(db.entries) == 1
        val0 = list(db.entries.values())[0]

        db_flags = IM.message.DbFlags(True, False, True)
        right0 = IM.db.DeviceEntry(remote_addr, remote_group, val0.mem_loc,
                                   db_flags, data, db=db)
        assert right0 == val0

        # Add again w/ a different local group
        data2 = bytes([0x50, 0x00, 0x02])
        db.add_on_device(remote_addr, remote_group, is_controller, data2)
        assert len(db.entries) == 2

        val1 = list(db.entries.values())[1]

        db_flags = IM.message.DbFlags(True, False, True)
        right1 = IM.db.DeviceEntry(remote_addr, remote_group, val1.mem_loc,
                                   db_flags, data2, db=None)
        assert right1 == val1


#===========================================================================
class MockDevice:
    """Mock insteon_mqtt/Device class
    """
    def __init__(self):
        self.sent = []

    def send(self, msg, handler, priority=None, after=None):
        self.sent.append(H.Data(msg=msg, handler=handler))

        # This is basically what the db modify is doing when it get's a ACK
        # of the db add message.  So we're just short circuiting that and
        # pretending the message came back.
        if isinstance(handler, IM.handler.DeviceDbModify):
            handler.db.add_entry(handler.entry)
            handler.on_done(True, "update", handler.entry)
