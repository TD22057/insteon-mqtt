#===========================================================================
#
# Tests for: insteont_mqtt/db/Modem.py
#
#===========================================================================
import insteon_mqtt as IM


class Test_Modem:
    #-----------------------------------------------------------------------
    def test_basic(self):
        obj = IM.db.Modem()
        assert len(obj) == 0

        addr = IM.Address('12.34.ab')
        data = bytes([0xff, 0x00, 0x00])
        e = IM.db.ModemEntry(addr, 0x01, True, data)
        obj.add_entry(e)

        addr = IM.Address('12.34.ac')
        data = bytes([0xff, 0x00, 0x00])
        e = IM.db.ModemEntry(addr, 0x01, True, data)
        obj.add_entry(e)

        addr = IM.Address('12.34.ad')
        data = bytes([0xff, 0x00, 0x00])
        e = IM.db.ModemEntry(addr, 0x02, True, data)
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
    def test_rec(self):
        obj = IM.db.Modem()

        b = bytes([0x02, 0x57,
                   0xe2,  # flags
                   0x01,  # group
                   0x3a, 0x29, 0x84,  # addess
                   0x01, 0x0e, 0x43])  # data
        msg = IM.message.InpAllLinkRec.from_bytes(b)
        obj.handle_db_rec(msg)

        rec = obj.entries[0]
        addr = IM.Address(0x3a, 0x29, 0x84)
        assert rec.addr == addr
        assert rec.group == 0x01
        assert rec.is_controller is True
        assert rec.is_responder is False
        assert rec.data == bytes([0x01, 0x0e, 0x43])

        # Update existing data
        data = bytes([0xff, 0x00, 0x00])
        e = IM.db.ModemEntry(addr, 0x01, True, data)
        obj.add_entry(e)

        assert len(obj) == 1

        assert obj.entries[0].data == data
