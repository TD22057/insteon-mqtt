#===========================================================================
#
# Tests for: insteont_mqtt/message/InpAllLinkComplete.py
#
#===========================================================================
import insteon_mqtt.message as Msg


class Test_InpAllLinkComplete:
    #-----------------------------------------------------------------------
    def test_controller(self):
        b = bytes([0x02, 0x53,  # code
                   0x01, 0x02,  # link, group
                   0x03, 0x04, 0x05,  # address
                   0x06, 0x07, 0x08])  # data
        obj = Msg.InpAllLinkComplete.from_bytes(b)

        assert obj.cmd == Msg.InpAllLinkComplete.Cmd.CONTROLLER
        assert obj.group == 0x02
        assert obj.addr.ids == [0x03, 0x04, 0x05]
        assert obj.dev_cat == 0x06
        assert obj.dev_subcat == 0x07
        assert obj.firmware == 0x08

        str(obj)

    #-----------------------------------------------------------------------
    def test_responder(self):
        b = bytes([0x02, 0x53,  # code
                   0x00, 0x02,  # link, group
                   0x03, 0x04, 0x05,  # address
                   0x06, 0x07, 0x08])  # data
        obj = Msg.InpAllLinkComplete.from_bytes(b)

        assert obj.cmd == Msg.InpAllLinkComplete.Cmd.RESPONDER
        assert obj.group == 0x02
        assert obj.addr.ids == [0x03, 0x04, 0x05]
        assert obj.dev_cat == 0x06
        assert obj.dev_subcat == 0x07
        assert obj.firmware == 0x08

        str(obj)

    #-----------------------------------------------------------------------
    def test_delete(self):
        b = bytes([0x02, 0x53,  # code
                   0xff, 0x02,  # link, group
                   0x03, 0x04, 0x05,  # address
                   0x06, 0x07, 0x08])  # data
        obj = Msg.InpAllLinkComplete.from_bytes(b)

        assert obj.cmd == Msg.InpAllLinkComplete.Cmd.DELETE
        assert obj.group == 0x02
        assert obj.addr.ids == [0x03, 0x04, 0x05]
        assert obj.dev_cat == 0x06
        assert obj.dev_subcat == 0x07
        assert obj.firmware == 0x08

        str(obj)

    #-----------------------------------------------------------------------


#===========================================================================
