#===========================================================================
#
# Tests for: insteont_mqtt/db/DeviceEntry.py
#
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_DeviceEntryI1:
    #-----------------------------------------------------------------------
    def test_i1(self):
        addr = IM.Address('20.c4.ba')
        ctrl = Msg.DbFlags(in_use=True, is_controller=True, is_last_rec=False)
        mem_loc = (0x0F << 8) + 0xFF
        data = bytes([0xFE, 0x1F, 0x00])
        entry = IM.db.DeviceEntry.from_i1_bytes(bytes([0x0F, 0xFF, 0xE2, 0x01,
                                                       0x20, 0xC4, 0xBA, 0xFE,
                                                       0x1F, 0x00]), db=None)

        assert entry.addr == addr
        assert entry.group == 0x01
        assert entry.db_flags.in_use == ctrl.in_use
        assert entry.db_flags.is_controller == ctrl.is_controller
        assert entry.db_flags.is_last_rec == ctrl.is_last_rec
        assert entry.mem_loc == mem_loc
        assert entry.data == data

        str(entry)

    #-----------------------------------------------------------------------
