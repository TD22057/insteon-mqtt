#===========================================================================
#
# Tests for: insteont_mqtt/message/OutModemInfo.py
#
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_OutModemInfo:
    #-----------------------------------------------------------------------
    def test_out(self):
        obj = Msg.OutModemInfo()
        assert obj.fixed_msg_size == 9

        b = obj.to_bytes()
        rt = bytes([0x02, 0x60])
        assert b == rt

        str(obj)

    #-----------------------------------------------------------------------
    def test_in(self):
        b = bytes([0x02, 0x60, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x06])
        obj = Msg.OutModemInfo.from_bytes(b)

        assert obj.is_ack is True
        assert obj.addr == IM.Address('11.22.33')
        assert obj.dev_cat == 0x44
        assert obj.sub_cat == 0x55
        assert obj.firmware == 0x66

        str(obj)

    #-----------------------------------------------------------------------


#===========================================================================
