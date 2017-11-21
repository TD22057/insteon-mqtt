#===========================================================================
#
# Tests for: insteont_mqtt/message/OutExtended.py
#
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_OutExtended:
    #-----------------------------------------------------------------------
    def test_basic(self):
        flag = Msg.Flags(0b100, True)
        b = bytes([0x02, 0x62,  # code
                   0x3e, 0xe2, 0xc4,  # addr
                   flag.byte,  # flags
                   0x11, 0x01,  # cmd1, cmd2
                   # extended data
                   0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
                   0x0a, 0x0b, 0x0c, 0x0d, 0x0e,
                   0x06])  # ack
        obj = Msg.OutExtended.from_bytes(b)

        assert obj.to_addr.ids == [0x3e, 0xe2, 0xc4]
        assert obj.flags.type == Msg.Flags.Type.BROADCAST
        assert obj.flags.is_ext is True
        assert obj.flags.hops_left == 3
        assert obj.flags.max_hops == 3
        assert obj.flags.is_nak is False
        assert obj.flags.is_broadcast is False
        assert obj.cmd1 == 0x11
        assert obj.cmd2 == 0x01
        assert obj.is_ack is True
        assert obj.data == bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
                                  0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e])

        assert obj.msg_size(b) == Msg.OutExtended.fixed_msg_size

        ob = obj.to_bytes()
        assert ob == b[:-1]  # output has no ack

        str(obj)

    #-----------------------------------------------------------------------
    def test_direct(self):
        addr = IM.Address(0x3e, 0xe2, 0xc4)
        data = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
                      0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e])
        obj = Msg.OutExtended.direct(addr, 0x11, 0x25, data)

        assert obj.to_addr.ids == [0x3e, 0xe2, 0xc4]
        assert obj.flags.type == Msg.Flags.Type.DIRECT
        assert obj.flags.is_ext is True
        assert obj.flags.hops_left == 3
        assert obj.flags.max_hops == 3
        assert obj.flags.is_nak is False
        assert obj.flags.is_broadcast is False
        assert obj.cmd1 == 0x11
        assert obj.cmd2 == 0x25
        assert obj.is_ack is None
        assert obj.data == data

#===========================================================================
