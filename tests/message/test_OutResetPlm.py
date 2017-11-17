#===========================================================================
#
# Tests for: insteont_mqtt/message/OutResetPlm.py
#
#===========================================================================
import insteon_mqtt.message as Msg
import pytest

#===========================================================================
class Test_OutResetPlm:
    #-----------------------------------------------------------------------
    def test_out(self):
        obj = Msg.OutResetPlm()
        assert obj.fixed_msg_size == 3

        b = obj.to_bytes()
        rt = bytes([0x02, Msg.OutResetPlm.msg_code])
        assert b == rt

        str(obj)

    #-----------------------------------------------------------------------
    def test_in(self):
        b = bytes([0x02, Msg.OutResetPlm.msg_code, 0x06])
        obj = Msg.OutResetPlm.from_bytes(b)

        assert obj.is_ack == True

        str(obj)

    #-----------------------------------------------------------------------


#===========================================================================
