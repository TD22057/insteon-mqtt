#===========================================================================
#
# Tests for: insteont_mqtt/message/OutGetModemFlags.py
#
#===========================================================================
import insteon_mqtt.message as Msg


class Test_OutGetModemFlags:
    #-----------------------------------------------------------------------
    def test_out(self):
        obj = Msg.OutGetModemFlags()
        assert obj.fixed_msg_size == 6

        b = obj.to_bytes()
        rt = bytes([0x02, 0x73])
        assert b == rt

        str(obj)

    #-----------------------------------------------------------------------
    def test_in_ack(self):
        b = bytes([0x02, 0x73, 0x01, 0x02, 0x03, 0x06])
        obj = Msg.OutGetModemFlags.from_bytes(b)
        assert obj.is_ack is True
        assert obj.modem_flags == 0x01
        assert obj.spare1 == 0x02
        assert obj.spare2 == 0x03

        str(obj)

    #-----------------------------------------------------------------------
    def test_in_nack(self):
        b = bytes([0x02, 0x73, 0x01, 0x02, 0x03, 0x15])
        obj = Msg.OutGetModemFlags.from_bytes(b)
        assert obj.is_ack is False
        assert obj.modem_flags == 0x01
        assert obj.spare1 == 0x02
        assert obj.spare2 == 0x03

        str(obj)


    #-----------------------------------------------------------------------


#===========================================================================
