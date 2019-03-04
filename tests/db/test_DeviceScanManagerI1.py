#===========================================================================
#
# Tests for: insteont_mqtt/db/DeviceScanManagerI1.py
#
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_Device:
    #-----------------------------------------------------------------------
    def test_start_scan(self):
        # tests start_scan and _set_msb
        device = MockDevice()
        device_db = IM.db.Device(IM.Address(0x01, 0x02, 0x03))
        manager = IM.db.DeviceScanManagerI1(device, device_db)

        db_msg = Msg.OutStandard.direct(device_db.addr, 0x28, 0x0F)

        manager.start_scan()
        assert device.msgs[0].to_bytes() == db_msg.to_bytes()

    #-----------------------------------------------------------------------
    def test_handle_set_msb(self):
        # tests handle_set_msb
        device = MockDevice()
        device_db = IM.db.Device(IM.Address(0x01, 0x02, 0x03))
        manager = IM.db.DeviceScanManagerI1(device, device_db)
        on_done = None
        manager.msb = 0x0F

        # Test bad MSB, should cause resend of set msb
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device_db.addr, device_db.addr, flags, 0x28,
                              0x0E)
        db_msg = Msg.OutStandard.direct(device_db.addr, 0x28, 0x0F)
        manager.handle_set_msb(msg, on_done)
        assert device.msgs[0].to_bytes() == db_msg.to_bytes()

        # Test receive correct msb
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device_db.addr, device_db.addr, flags, 0x28,
                              0x0F)
        db_msg = Msg.OutStandard.direct(device_db.addr, 0x2B, 0xF8)
        manager.handle_set_msb(msg, on_done)
        assert device.msgs[1].to_bytes() == db_msg.to_bytes()

    #-----------------------------------------------------------------------
    def test_handle_get_lsb(self):
        # tests handle_get_lsb
        device = MockDevice()
        device_db = IM.db.Device(IM.Address(0x01, 0x02, 0x03))
        manager = IM.db.DeviceScanManagerI1(device, device_db)
        on_done = None
        manager.msb = 0x0F
        calls = []

        def callback(success, msg, data):
            calls.append(msg)

        # Test receiving a record e2 01   3a 29 84    01 0e 43
        # Link Flag
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device_db.addr, device_db.addr, flags, 0x2B,
                              0xE2)
        db_msg = Msg.OutStandard.direct(device_db.addr, 0x2B, 0xF9)
        manager.handle_get_lsb(msg, on_done)
        assert device.msgs[0].to_bytes() == db_msg.to_bytes()
        assert len(manager.record) == 1

        # Group
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device_db.addr, device_db.addr, flags, 0x2B,
                              0x01)
        db_msg = Msg.OutStandard.direct(device_db.addr, 0x2B, 0xFA)
        manager.handle_get_lsb(msg, on_done)
        assert device.msgs[1].to_bytes() == db_msg.to_bytes()
        assert len(manager.record) == 2

        # Address High
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device_db.addr, device_db.addr, flags, 0x2B,
                              0x3A)
        db_msg = Msg.OutStandard.direct(device_db.addr, 0x2B, 0xFB)
        manager.handle_get_lsb(msg, on_done)
        assert device.msgs[2].to_bytes() == db_msg.to_bytes()
        assert len(manager.record) == 3

        # Address Mid
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device_db.addr, device_db.addr, flags, 0x2B,
                              0x29)
        db_msg = Msg.OutStandard.direct(device_db.addr, 0x2B, 0xFC)
        manager.handle_get_lsb(msg, on_done)
        assert device.msgs[3].to_bytes() == db_msg.to_bytes()
        assert len(manager.record) == 4

        # Address Low
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device_db.addr, device_db.addr, flags, 0x2B,
                              0x84)
        db_msg = Msg.OutStandard.direct(device_db.addr, 0x2B, 0xFD)
        manager.handle_get_lsb(msg, on_done)
        assert device.msgs[4].to_bytes() == db_msg.to_bytes()
        assert len(manager.record) == 5

        # Address D1
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device_db.addr, device_db.addr, flags, 0x2B,
                              0x01)
        db_msg = Msg.OutStandard.direct(device_db.addr, 0x2B, 0xFE)
        manager.handle_get_lsb(msg, on_done)
        assert device.msgs[5].to_bytes() == db_msg.to_bytes()
        assert len(manager.record) == 6

        # Address D2
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device_db.addr, device_db.addr, flags, 0x2B,
                              0x0E)
        db_msg = Msg.OutStandard.direct(device_db.addr, 0x2B, 0xFF)
        manager.handle_get_lsb(msg, on_done)
        assert device.msgs[6].to_bytes() == db_msg.to_bytes()
        assert len(manager.record) == 7

        # Address D3
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device_db.addr, device_db.addr, flags, 0x2B,
                              0x43)
        db_msg = Msg.OutStandard.direct(device_db.addr, 0x2B, 0xF0)
        manager.handle_get_lsb(msg, on_done)
        assert device.msgs[7].to_bytes() == db_msg.to_bytes()
        assert len(manager.record) == 0

        db_flags = Msg.DbFlags(in_use=True, is_controller=True,
                               is_last_rec=False)
        raw = [0x00, 0x01,
               0x0F, 0xFF,  # mem_loc
               0x00, db_flags.to_bytes()[0],
               0x01,  # group
               0x3a, 0x29, 0x84,
               0x01, 0x0E, 0x43, 0x06]
        entry = IM.db.DeviceEntry.from_bytes(bytes(raw))

        assert len(device_db.entries) == 1
        assert len(device_db.unused) == 0
        assert len(device_db.groups) == 1

        grp = device_db.find_group(0x01)
        assert len(grp) == 1
        assert grp[0].to_bytes() == entry.to_bytes()

        # test changing MSB
        manager.record = [0xe2, 0x01, 3, 4, 5, 6, 7]
        manager.lsb = 0x07

        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device_db.addr, device_db.addr, flags, 0x2B,
                              0x08)
        manager.handle_get_lsb(msg, on_done)
        assert device.msgs[8].cmd2 == 0x0E

        # test on_done callback on last record
        flags = Msg.DbFlags(True, True, True)
        manager.record = [flags.to_bytes()[0], 0x01, 3, 4, 5, 6, 7]
        manager.lsb = 0xFF

        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device_db.addr, device_db.addr, flags, 0x2B,
                              0x08)
        manager.handle_get_lsb(msg, callback)
        assert calls[0] == "Database received"


#===========================================================================


class MockDevice:
    def __init__(self):
        self.msgs = []

    def send(self, msg, handler, high_priority=False, after=None):
        self.msgs.append(msg)
