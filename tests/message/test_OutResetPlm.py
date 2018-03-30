#===========================================================================
#
# Tests for: insteont_mqtt/message/OutResetPlm.py
#
#===========================================================================
import insteon_mqtt.message as Msg


class Test_OutResetPlm:
    #-----------------------------------------------------------------------
    def test_out(self):
        obj = Msg.OutResetModem()
        assert obj.fixed_msg_size == 3

        b = obj.to_bytes()
        rt = bytes([0x02, 0x67])
        assert b == rt

        str(obj)

    #-----------------------------------------------------------------------
    def test_in(self):
        b = bytes([0x02, 0x67, 0x06])
        obj = Msg.OutResetModem.from_bytes(b)

        assert obj.is_ack is True

        str(obj)

    #-----------------------------------------------------------------------


#===========================================================================
