#===========================================================================
#
# Tests for: insteont_mqtt/message/InpAllLinkFailure.py
#
#===========================================================================
import insteon_mqtt.message as Msg


class Test_InpAllLinkFailure:
    #-----------------------------------------------------------------------
    def test_basic(self):
        b = bytes([0x02, 0x56,  # code
                   0x02,  # group
                   0x03, 0x04, 0x05])  # address
        obj = Msg.InpAllLinkFailure.from_bytes(b)

        assert obj.group == 0x02
        assert obj.addr.ids == [0x03, 0x04, 0x05]

        str(obj)

    #-----------------------------------------------------------------------


#===========================================================================
