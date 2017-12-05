#===========================================================================
#
# Tests for: insteont_mqtt/message/InpAllLinkRec.py
#
#===========================================================================
import insteon_mqtt.message as Msg


class Test_InpAllLinkRec:
    #-----------------------------------------------------------------------
    def test_basic(self):
        b = bytes([0x02, 0x57,
                   0xe2,  # flags
                   0x01,  # group
                   0x3a, 0x29, 0x84,  # addess
                   0x01, 0x0e, 0x43])  # data
        obj = Msg.InpAllLinkRec.from_bytes(b)

        assert obj.db_flags.in_use is True
        assert obj.db_flags.is_controller is True
        assert obj.db_flags.is_last_rec is False

        assert obj.group == 0x01
        assert obj.addr.ids == [0x3a, 0x29, 0x84]
        assert obj.data == bytes([0x01, 0x0e, 0x43])

        str(obj)

    #-----------------------------------------------------------------------

#===========================================================================
