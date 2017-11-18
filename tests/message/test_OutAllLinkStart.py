#===========================================================================
#
# Tests for: insteont_mqtt/message/OutAllLinkStart.py
#
#===========================================================================
import insteon_mqtt.message as Msg
import pytest

#===========================================================================
class Test_OutAllLinkStart:
    #-----------------------------------------------------------------------
    def test_responder(self):
        b = bytes([0x02, 0x64,
                   0x01,  # responder
                   0x02,  # group
                   0x06])  # ack
        obj = Msg.OutAllLinkStart.from_bytes(b)

        assert obj.link == Msg.OutAllLinkStart.RESPONDER
        assert obj.plm_responder == True
        assert obj.plm_controller == False
        assert obj.is_delete == False
        assert obj.group == 0x02
        assert obj.is_ack == True

        ob = obj.to_bytes()
        assert ob == b[:-1]  # output doesn't have the ack byte

        str(obj)

    #-----------------------------------------------------------------------
    def test_controller(self):
        b = bytes([0x02, 0x64,
                   0x03,  # responder
                   0x02,  # group
                   0x06])  # ack
        obj = Msg.OutAllLinkStart.from_bytes(b)

        assert obj.link == Msg.OutAllLinkStart.CONTROLLER
        assert obj.plm_responder == False
        assert obj.plm_controller == True
        assert obj.is_delete == False
        assert obj.group == 0x02
        assert obj.is_ack == True

        ob = obj.to_bytes()
        assert ob == b[:-1]  # output doesn't have the ack byte

        str(obj)

    #-----------------------------------------------------------------------
    def test_delete(self):
        b = bytes([0x02, 0x64,
                   0xff,  # delete
                   0x02,  # group
                   0x15])  # ack
        obj = Msg.OutAllLinkStart.from_bytes(b)

        assert obj.link == Msg.OutAllLinkStart.DELETE
        assert obj.plm_responder == False
        assert obj.plm_controller == False
        assert obj.is_delete == True
        assert obj.group == 0x02
        assert obj.is_ack == False

        ob = obj.to_bytes()
        assert ob == b[:-1]  # output doesn't have the ack byte

        str(obj)

    #-----------------------------------------------------------------------


#===========================================================================
