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
