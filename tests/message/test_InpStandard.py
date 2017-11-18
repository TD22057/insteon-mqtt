#===========================================================================
#
# Tests for: insteont_mqtt/message/InpStandard.py
#
#===========================================================================
import insteon_mqtt.message as Msg


class Test_InpStandard:
    #-----------------------------------------------------------------------
    def test_basic(self):
        b = bytes([0x02, 0x50,  # code
                   0x3e, 0xe2, 0xc4,  # from addr
                   0x23, 0x9b, 0x65,  # to addr
                   0xaf,  # flags
                   0x11, 0x01])  # cmd1, cmd2
        obj = Msg.InpStandard.from_bytes(b)

        assert obj.from_addr.ids == [0x3e, 0xe2, 0xc4]
        assert obj.to_addr.ids == [0x23, 0x9b, 0x65]
        assert obj.flags.type == Msg.Flags.DIRECT_NAK
        assert obj.flags.is_ext is False
        assert obj.flags.hops_left == 3
        assert obj.flags.max_hops == 3
        assert obj.flags.is_nak is True
        assert obj.flags.is_broadcast is False
        assert obj.cmd1 == 0x11
        assert obj.cmd2 == 0x01
        assert obj.group is None

        str(obj)

    #-----------------------------------------------------------------------
    def test_broadcast(self):
        b = bytes([0x02, 0x50,  # code
                   0x3e, 0xe2, 0xc4,  # from addr
                   0x23, 0x9b, 0x65,  # to addr
                   0xcf,  # flags
                   0x11, 0x01])  # cmd1, cmd2
        obj = Msg.InpStandard.from_bytes(b)

        assert obj.from_addr.ids == [0x3e, 0xe2, 0xc4]
        assert obj.to_addr.ids == [0x23, 0x9b, 0x65]
        assert obj.flags.type == Msg.Flags.ALL_LINK_BROADCAST
        assert obj.flags.is_ext is False
        assert obj.flags.hops_left == 3
        assert obj.flags.max_hops == 3
        assert obj.flags.is_nak is False
        assert obj.flags.is_broadcast is True
        assert obj.cmd1 == 0x11
        assert obj.cmd2 == 0x01
        assert obj.group == 0x65

        str(obj)

    #-----------------------------------------------------------------------
    def test_cleanup(self):
        b = bytes([0x02, 0x50,  # code
                   0x3e, 0xe2, 0xc4,  # from addr
                   0x23, 0x9b, 0x65,  # to addr
                   0x6f,  # flags
                   0x11, 0x01])  # cmd1, cmd2
        obj = Msg.InpStandard.from_bytes(b)

        assert obj.from_addr.ids == [0x3e, 0xe2, 0xc4]
        assert obj.to_addr.ids == [0x23, 0x9b, 0x65]
        assert obj.flags.type == Msg.Flags.CLEANUP_ACK
        assert obj.flags.is_ext is False
        assert obj.flags.hops_left == 3
        assert obj.flags.max_hops == 3
        assert obj.flags.is_nak is False
        assert obj.flags.is_broadcast is False
        assert obj.cmd1 == 0x11
        assert obj.cmd2 == 0x01
        assert obj.group == 0x01

        str(obj)


#===========================================================================
