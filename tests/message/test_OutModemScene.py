#===========================================================================
#
# Tests for: insteont_mqtt/message/OutModemScene.py
#
#===========================================================================
import insteon_mqtt.message as Msg


class Test_OutModemScene:
    #-----------------------------------------------------------------------
    def test_basic(self):
        b = bytes([0x02, 0x61,  # code
                   0x01,  # group
                   0x11, 0x20,  # cmd1, cmd2
                   0x06])  # ack
        obj = Msg.OutModemScene.from_bytes(b)

        assert obj.group == 0x01
        assert obj.cmd1 == 0x11
        assert obj.cmd2 == 0x20
        assert obj.is_ack is True

        ob = obj.to_bytes()
        assert ob == b[:-1]  # output doesn't have the ack byte

        str(obj)

    #-----------------------------------------------------------------------


#===========================================================================
