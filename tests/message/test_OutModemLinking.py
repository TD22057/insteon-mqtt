#===========================================================================
#
# Tests for: insteont_mqtt/message/OutModemLinking.py
#
#===========================================================================
import insteon_mqtt.message as Msg


class Test_OutModemLinking:
    #-----------------------------------------------------------------------
    def test_responder(self):
        b = bytes([0x02, 0x64,
                   0x00,  # responder
                   0x02,  # group
                   0x06])  # ack
        obj = Msg.OutModemLinking.from_bytes(b)

        assert obj.cmd == Msg.OutModemLinking.Cmd.RESPONDER
        assert obj.group == 0x02
        assert obj.is_ack is True

        ob = obj.to_bytes()
        assert ob == b[:-1]  # output doesn't have the ack byte

        str(obj)

    #-----------------------------------------------------------------------
    def test_controller(self):
        b = bytes([0x02, 0x64,
                   0x01,  # controller
                   0x02,  # group
                   0x06])  # ack
        obj = Msg.OutModemLinking.from_bytes(b)

        assert obj.cmd == Msg.OutModemLinking.Cmd.CONTROLLER
        assert obj.group == 0x02
        assert obj.is_ack is True

        ob = obj.to_bytes()
        assert ob == b[:-1]  # output doesn't have the ack byte

        str(obj)

    #-----------------------------------------------------------------------
    def test_either(self):
        b = bytes([0x02, 0x64,
                   0x03,  # either
                   0x02,  # group
                   0x06])  # ack
        obj = Msg.OutModemLinking.from_bytes(b)

        assert obj.cmd == Msg.OutModemLinking.Cmd.EITHER
        assert obj.group == 0x02
        assert obj.is_ack is True

        ob = obj.to_bytes()
        assert ob == b[:-1]  # output doesn't have the ack byte

        str(obj)

    #-----------------------------------------------------------------------
    def test_delete(self):
        b = bytes([0x02, 0x64,
                   0xff,  # delete
                   0x02,  # group
                   0x15])  # ack
        obj = Msg.OutModemLinking.from_bytes(b)

        assert obj.cmd == Msg.OutModemLinking.Cmd.DELETE
        assert obj.group == 0x02
        assert obj.is_ack is False

        ob = obj.to_bytes()
        assert ob == b[:-1]  # output doesn't have the ack byte

        str(obj)

    #-----------------------------------------------------------------------


#===========================================================================
