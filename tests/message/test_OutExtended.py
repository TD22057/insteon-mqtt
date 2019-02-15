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
                   flag.to_bytes()[0],  # flags
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

        obj.crc_type = None
        ob = obj.to_bytes()
        assert ob == b[:-1]  # output has no ack

        # Test CRC computations.  No good way to generate right
        # answers for these so these came from inspection.
        obj.crc_type = "D14"
        ob = obj.to_bytes()
        raw = list(b[:-1])  # output has no ack
        raw[21] = 0x85
        assert ob == bytes(raw)

        obj.crc_type = "CRC"
        ob = obj.to_bytes()
        raw = list(b[:-1])  # output has no ack
        raw[20] = 0x41
        raw[21] = 0xf8
        assert ob == bytes(raw)

        str(obj)

    #-----------------------------------------------------------------------
    def test_direct(self):
        addr = IM.Address(0x3e, 0xe2, 0xc4)
        data = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
                      0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e])
        obj = Msg.OutExtended.direct(addr, 0x11, 0x25, data, crc_type=None)

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
        assert obj.crc_type == None

#===========================================================================
