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
        obj = IM.db.ModemEntry(addr, 0x03, True, data)

        assert obj.addr == addr
        assert obj.group == 0x03
        assert obj.is_controller is True
        assert obj.is_responder is False
        assert obj.data == data
        assert obj.on_level == data[0]
        assert obj.ramp_rate == data[1]

        d = obj.to_json()
        obj2 = IM.db.ModemEntry.from_json(d)
        assert obj2.addr == obj.addr
        assert obj2.group == obj.group
        assert obj2.is_controller == obj.is_controller
        assert obj2.is_responder == obj.is_responder
        assert obj2.data == obj.data
        assert obj2.on_level == obj.on_level
        assert obj2.ramp_rate == obj.ramp_rate

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
        obj = IM.db.ModemEntry(addr, 0x03, False, data)

        assert obj.addr == addr
        assert obj.group == 0x03
        assert obj.is_controller is False
        assert obj.is_responder is True
        assert obj.data == data
        assert obj.on_level == data[0]
        assert obj.ramp_rate == data[1]

        d = obj.to_json()
        obj2 = IM.db.ModemEntry.from_json(d)
        assert obj2.addr == obj.addr
        assert obj2.group == obj.group
        assert obj2.is_controller == obj.is_controller
        assert obj2.is_responder == obj.is_responder
        assert obj2.data == obj.data
        assert obj2.on_level == obj.on_level
        assert obj2.ramp_rate == obj.ramp_rate

        assert obj2 == obj
        obj2.group = 0x01
        assert obj2 != obj

        str(obj)

    #-----------------------------------------------------------------------


#===========================================================================
