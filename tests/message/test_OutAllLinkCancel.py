#===========================================================================
#
# Tests for: insteont_mqtt/message/OutAllLinkCancel.py
#
#===========================================================================
import insteon_mqtt.message as Msg
import pytest

#===========================================================================
class Test_OutAllLinkCancel:
    #-----------------------------------------------------------------------
    def test_out(self):
        obj = Msg.OutAllLinkCancel()
        assert obj.fixed_msg_size == 3

        b = obj.to_bytes()
        rt = bytes([0x02, 0x65])
        assert b == rt

        str(obj)

    #-----------------------------------------------------------------------
    def test_in(self):
        b = bytes([0x02, 0x65, 0x06])
        obj = Msg.OutAllLinkCancel.from_bytes(b)

        assert obj.is_ack == True

        str(obj)

    #-----------------------------------------------------------------------


#===========================================================================
