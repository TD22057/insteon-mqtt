#===========================================================================
#
# Tests for: insteont_mqtt/message/InpStandard.py
#
#===========================================================================
import insteon_mqtt as IM
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
        assert obj.flags.type == Msg.Flags.Type.DIRECT_NAK
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
        assert obj.flags.type == Msg.Flags.Type.ALL_LINK_BROADCAST
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
        assert obj.flags.type == Msg.Flags.Type.CLEANUP_ACK
        assert obj.flags.is_ext is False
        assert obj.flags.hops_left == 3
        assert obj.flags.max_hops == 3
        assert obj.flags.is_nak is False
        assert obj.flags.is_broadcast is False
        assert obj.cmd1 == 0x11
        assert obj.cmd2 == 0x01
        assert obj.group == 0x01

        str(obj)

    #-----------------------------------------------------------------------
    def test_is_duplicate(self):
        b = bytes([0x02, 0x50,  # code
                   0x3e, 0xe2, 0xc4,  # from addr
                   0x23, 0x9b, 0x65,  # to addr
                   0x6f,  # flags 3 max_hops and 3 hops_left
                   0x11, 0x01])  # cmd1, cmd2
        obj = Msg.InpStandard.from_bytes(b)

        b2 = bytes([0x02, 0x50,  # code
                    0x3e, 0xe2, 0xc4,  # from addr
                    0x23, 0x9b, 0x65,  # to addr
                    0x65,  # flags 1 max_hops and 1 hops_left
                    0x11, 0x01])  # cmd1, cmd2
        obj2 = Msg.InpStandard.from_bytes(b2)

        assert obj == obj2

        # wrong from address
        b3 = bytes([0x02, 0x50,  # code
                    0x01, 0xe2, 0xc4,  # from addr
                    0x23, 0x9b, 0x65,  # to addr
                    0x65,  # flags 1 max_hops and 1 hops_left
                    0x11, 0x01])  # cmd1, cmd2
        obj3 = Msg.InpStandard.from_bytes(b3)

        assert obj != obj3

        # wrong cmd 1
        b4 = bytes([0x02, 0x50,  # code
                    0x3e, 0xe2, 0xc4,  # from addr
                    0x23, 0x9b, 0x65,  # to addr
                    0x65,  # flags 1 max_hops and 1 hops_left
                    0x12, 0x01])  # cmd1, cmd2
        obj4 = Msg.InpStandard.from_bytes(b4)

        assert obj != obj4

        # wrong cmd 2
        b5 = bytes([0x02, 0x50,  # code
                    0x3e, 0xe2, 0xc4,  # from addr
                    0x23, 0x9b, 0x65,  # to addr
                    0x65,  # flags 1 max_hops and 1 hops_left
                    0x11, 0x02])  # cmd1, cmd2
        obj5 = Msg.InpStandard.from_bytes(b5)

        assert obj != obj5

        assert obj != [1, 2, 3]

    #-----------------------------------------------------------------------
    def test_nak_str(self):
        from_addr = IM.Address(0x01, 0x02, 0x03)
        to_addr = IM.Address(0x03, 0x05, 0x07)

        # ID not in DB error
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_NAK, False)
        obj = Msg.InpStandard(from_addr, to_addr, flags, 0x00, 0xFF)
        nak_str = obj.nak_str()
        assert len(nak_str) > 0

        # unknow error type
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_NAK, False)
        obj = Msg.InpStandard(from_addr, to_addr, flags, 0x00, 0x10)
        nak_str = obj.nak_str()
        assert len(nak_str) == 0

        # not a nak
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        obj = Msg.InpStandard(from_addr, to_addr, flags, 0x00, 0xFF)
        nak_str = obj.nak_str()
        assert len(nak_str) == 0


#===========================================================================
