#===========================================================================
#
# Tests for: insteont_mqtt/message/OutAllLinkUpdate.py
#
#===========================================================================
import insteon_mqtt.message as Msg


class Test_OutAllLinkUpdate:
    #-----------------------------------------------------------------------
    def test_basic(self):
        b = bytes([0x02, 0x6f,  # code
                   0x40,  # cmd
                   0x42,  # db flags
                   0x03,  # group
                   0x32, 0xf4, 0x22,  # address
                   0x01, 0x02, 0x03,  # data
                   0x06])  # ack
        obj = Msg.OutAllLinkUpdate.from_bytes(b)

        assert obj.cmd == Msg.OutAllLinkUpdate.Cmd.ADD_CONTROLLER
        assert obj.group == 0x03
        assert obj.db_flags.in_use is False
        assert obj.db_flags.is_controller is True
        assert obj.db_flags.last_record is False
        assert obj.addr.ids == [0x32, 0xf4, 0x22]
        assert obj.data == bytes([0x01, 0x02, 0x03])
        assert obj.is_ack is True

        ob = obj.to_bytes()
        assert ob == b[:-1]  # output has no ack byte

        str(obj)

    #-----------------------------------------------------------------------


#===========================================================================
