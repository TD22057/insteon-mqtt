#===========================================================================
#
# Tests for: insteont_mqtt/db/DeviceModifyManagerI1.py
#
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_Device:
    #-----------------------------------------------------------------------
    def test_start_modify(self):
        # tests start_modify and _set_msb
        protocol = MockProto()
        modem = MockModem()
        addr = IM.Address(0x01, 0x02, 0x03)
        device = IM.device.Base(protocol, modem, addr)

        # Create the new entry at the current last memory location.
        db_flags = Msg.DbFlags(in_use=True, is_controller=True,
                               is_last_rec=False)
        i1_entry = IM.db.DeviceEntry(addr, 0x01, device.db.last.mem_loc,
                                     db_flags, None)

        manager = IM.db.DeviceModifyManagerI1(device,
                                              device.db,
                                              i1_entry.to_i1_bytes())

        db_msg = Msg.OutStandard.direct(device.addr, 0x28, 0x0F)

        manager.start_modify()
        assert protocol.msgs[0].to_bytes() == db_msg.to_bytes()

    #-----------------------------------------------------------------------
    def test_handle_set_msb(self):
        # tests handle_set_msb and get_next_lsb
        protocol = MockProto()
        modem = MockModem()
        addr = IM.Address(0x01, 0x02, 0x03)
        device = IM.device.Base(protocol, modem, addr)

        # Create the new entry at the current last memory location.
        db_flags = Msg.DbFlags(in_use=True, is_controller=True,
                               is_last_rec=False)
        i1_entry = IM.db.DeviceEntry(addr, 0x01, device.db.last.mem_loc,
                                     db_flags, None)

        manager = IM.db.DeviceModifyManagerI1(device,
                                              device.db,
                                              i1_entry.to_i1_bytes())

        # Test bad MSB, should cause resend of set msb
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device.addr, device.addr, flags, 0x28, 0x0E)
        db_msg = Msg.OutStandard.direct(device.addr, 0x28, 0x0F)
        manager.handle_set_msb(msg, None)
        assert protocol.msgs[0].to_bytes() == db_msg.to_bytes()

        # Test receive correct msb
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device.addr, device.addr, flags, 0x28, 0x0F)
        db_msg = Msg.OutStandard.direct(device.addr, 0x2B, 0xF8)
        manager.handle_set_msb(msg, None)
        assert protocol.msgs[1].to_bytes() == db_msg.to_bytes()

    #-----------------------------------------------------------------------
    def test_handle_lsb_response(self):
        # tests handle_lsb_response and write_lsb_byte
        protocol = MockProto()
        modem = MockModem()
        addr = IM.Address(0x01, 0x02, 0x03)
        device = IM.device.Base(protocol, modem, addr)

        # Create the new entry at the current last memory location.
        db_flags = Msg.DbFlags(in_use=True, is_controller=True,
                               is_last_rec=False)
        i1_entry = IM.db.DeviceEntry(addr, 0x01, device.db.last.mem_loc,
                                     db_flags, None)

        manager = IM.db.DeviceModifyManagerI1(device,
                                              device.db,
                                              i1_entry.to_i1_bytes())

        # Test wrong LSB, should cause poke of set lsb
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device.addr, device.addr, flags, 0x2B, 0xA2)
        db_msg = Msg.OutStandard.direct(device.addr, 0x29, 0xE2)
        manager.handle_lsb_response(msg, None)
        assert protocol.msgs[0].to_bytes() == db_msg.to_bytes()

        # Test receive correct lsb, should cause request for next lsb
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device.addr, device.addr, flags, 0x29, 0xE2)
        db_msg = Msg.OutStandard.direct(device.addr, 0x2B, 0xF9)
        manager.handle_lsb_response(msg, None)
        assert protocol.msgs[1].to_bytes() == db_msg.to_bytes()

    #-----------------------------------------------------------------------
    def test_finish_write(self):
        # tests the finished entry in advance_lsb
        protocol = MockProto()
        modem = MockModem()
        addr = IM.Address(0x01, 0x02, 0x03)
        device = IM.device.Base(protocol, modem, addr)
        calls = []

        def callback(success, msg, data):
            calls.append(msg)

        # Create the new entry at the current last memory location.
        db_flags = Msg.DbFlags(in_use=False, is_controller=True,
                               is_last_rec=False)
        i1_entry = IM.db.DeviceEntry(addr, 0x01, device.db.last.mem_loc,
                                     db_flags, None)

        manager = IM.db.DeviceModifyManagerI1(device,
                                              device.db,
                                              i1_entry.to_i1_bytes())

        # Test received unused from start
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device.addr, device.addr, flags, 0x2B, 0x62)
        manager.handle_lsb_response(msg, callback)
        assert calls[0] == "Database entry written"

        # Test received the last byte
        manager.record_index = 7
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(device.addr, device.addr, flags, 0x29, 0x00)
        manager.handle_lsb_response(msg, callback)
        assert calls[1] == "Database entry written"


#===========================================================================


class MockProto:
    def __init__(self):
        self.msgs = []

    def send(self, msg, handler, high_priority=False, after=None):
        self.msgs.append(msg)


class MockModem():
    def __init__(self):
        self.save_path = ''
