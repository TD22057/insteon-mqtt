#===========================================================================
#
# Tests for: insteont_mqtt/message/OutAllLinkGetNext.py
#
#===========================================================================
import insteon_mqtt.message as Msg
import pytest

#===========================================================================
class Test_OutAllLinkGetNext:
    #-----------------------------------------------------------------------
    def test_out(self):
        obj = Msg.OutAllLinkGetNext()
        assert obj.fixed_msg_size == 3

        b = obj.to_bytes()
        rt = bytes([0x02, 0x6a])
        assert b == rt

        str(obj)

    #-----------------------------------------------------------------------
    def test_in(self):
        b = bytes([0x02, 0x6a, 0x06])
        obj = Msg.OutAllLinkGetNext.from_bytes(b)

        assert obj.is_ack == True

        str(obj)

    #-----------------------------------------------------------------------


#===========================================================================
