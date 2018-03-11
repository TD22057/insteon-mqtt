#===========================================================================
#
# Tests for: insteont_mqtt/message/InpExtended.py
#
#===========================================================================
import insteon_mqtt.message as Msg


class Test_InpExtended:
    #-----------------------------------------------------------------------
    def test_basic(self):
        b = bytes([0x02, 0x51,  # code
                   0x3e, 0xe2, 0xc4,  # from addr
                   0x23, 0x9b, 0x65,  # to addr
                   0xbf,  # flags
                   0x11, 0x01,  # cmd1, cmd2
                   # extended bytes
                   0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
                   0x0a, 0x0b, 0x0c, 0x0d, 0x0e])
        obj = Msg.InpExtended.from_bytes(b)

        assert obj.from_addr.ids == [0x3e, 0xe2, 0xc4]
        assert obj.to_addr.ids == [0x23, 0x9b, 0x65]
        assert obj.flags.type == Msg.Flags.Type.DIRECT_NAK
        assert obj.flags.is_ext is True
        assert obj.flags.hops_left == 3
        assert obj.flags.max_hops == 3
        assert obj.flags.is_nak is True
        assert obj.flags.is_broadcast is False
        assert obj.cmd1 == 0x11
        assert obj.cmd2 == 0x01
        assert obj.group is None
        assert obj.data == bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06,
                                  0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c,
                                  0x0d, 0x0e])

        str(obj)

    #-----------------------------------------------------------------------
    def test_broadcast(self):
        b = bytes([0x02, 0x51,  # code
                   0x3e, 0xe2, 0xc4,  # from addr
                   0x23, 0x9b, 0x65,  # to addr
                   0xdf,  # flags
                   0x11, 0x01,  # cmd1, cmd2
                   # extended bytes
                   0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
                   0x0a, 0x0b, 0x0c, 0x0d, 0x0e])
        obj = Msg.InpExtended.from_bytes(b)

        assert obj.from_addr.ids == [0x3e, 0xe2, 0xc4]
        assert obj.to_addr.ids == [0x23, 0x9b, 0x65]
        assert obj.flags.type == Msg.Flags.Type.ALL_LINK_BROADCAST
        assert obj.flags.is_ext is True
        assert obj.flags.hops_left == 3
        assert obj.flags.max_hops == 3
        assert obj.flags.is_nak is False
        assert obj.flags.is_broadcast is True
        assert obj.cmd1 == 0x11
        assert obj.cmd2 == 0x01
        assert obj.group == 0x65
        assert obj.data == bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06,
                                  0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c,
                                  0x0d, 0x0e])

        str(obj)

    #-----------------------------------------------------------------------
    def test_cleanup(self):
        b = bytes([0x02, 0x51,  # code
                   0x3e, 0xe2, 0xc4,  # from addr
                   0x23, 0x9b, 0x65,  # to addr
                   0x7f,  # flags
                   0x11, 0x01,  # cmd1, cmd2
                   # extended bytes
                   0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
                   0x0a, 0x0b, 0x0c, 0x0d, 0x0e])
        obj = Msg.InpExtended.from_bytes(b)

        assert obj.from_addr.ids == [0x3e, 0xe2, 0xc4]
        assert obj.to_addr.ids == [0x23, 0x9b, 0x65]
        assert obj.flags.type == Msg.Flags.Type.CLEANUP_ACK
        assert obj.flags.is_ext is True
        assert obj.flags.hops_left == 3
        assert obj.flags.max_hops == 3
        assert obj.flags.is_nak is False
        assert obj.flags.is_broadcast is False
        assert obj.cmd1 == 0x11
        assert obj.cmd2 == 0x01
        assert obj.group == 0x01
        assert obj.data == bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06,
                                  0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c,
                                  0x0d, 0x0e])

        str(obj)

    #-----------------------------------------------------------------------
    def test_is_duplicate(self):
        b = bytes([0x02, 0x51,  # code
                   0x3e, 0xe2, 0xc4,  # from addr
                   0x23, 0x9b, 0x65,  # to addr
                   0x7f,  # flags 3 max_hops and 3 hops_left
                   0x11, 0x01,  # cmd1, cmd2
                   # extended bytes
                   0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
                   0x0a, 0x0b, 0x0c, 0x0d, 0x0e])
        obj = Msg.InpExtended.from_bytes(b)

        b2 = bytes([0x02, 0x51,  # code
                   0x3e, 0xe2, 0xc4,  # from addr
                   0x23, 0x9b, 0x65,  # to addr
                   0x75,  # flags 1 max_hops and 1 hops_left
                   0x11, 0x01,  # cmd1, cmd2
                   # extended bytes
                   0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
                   0x0a, 0x0b, 0x0c, 0x0d, 0x0e])
        obj2 = Msg.InpExtended.from_bytes(b2)

        assert obj.is_duplicate(obj2) is True

        str(obj)

#===========================================================================
