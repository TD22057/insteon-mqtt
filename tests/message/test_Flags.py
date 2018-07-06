#===========================================================================
#
# Tests for: insteont_mqtt/message/Flags.py
#
#===========================================================================
import insteon_mqtt.message as Msg


class Test_DbFlags:
    #-----------------------------------------------------------------------
    def check(self, obj, type, is_ext, hops, max_hops, nak, broadcast, raw):
        assert obj.type == type
        assert obj.is_ext == is_ext
        assert obj.hops_left == hops
        assert obj.max_hops == max_hops
        assert obj.is_nak == nak
        assert obj.is_broadcast == broadcast

        out = obj.to_bytes()
        assert len(out) == 1
        assert out[0] == raw

        str(obj)

    #-----------------------------------------------------------------------
    def test_basic(self):
        b = bytes([
            0b00000011,
            0b00110110,
            0b01001001,
            0b01111100,
            0b10000011,
            0b10110110,
            0b11001001,
            0b11111100,
            ])
        type = [0, 1, 2, 3, 4, 5, 6, 7]
        ext = [0, 1, 0, 1, 0, 1, 0, 1]
        hops = [0, 1, 2, 3, 0, 1, 2, 3]
        max_hops = [3, 2, 1, 0, 3, 2, 1, 0]

        for i in range(len(b)):  # noqa
            obj = Msg.Flags.from_bytes(b, i)
            self.check(obj, type[i], ext[i], hops[i], max_hops[i],
                       type[i] == 5 or type[i] == 7, type[i] == 6, b[i])

    #-----------------------------------------------------------------------
    def test_eq(self):
        msg1 = Msg.Flags(Msg.Flags.Type.BROADCAST, False)

        msg2 = Msg.Flags(Msg.Flags.Type.BROADCAST, False, 2, 3)
        assert msg1 == msg2

        msg3 = Msg.Flags(Msg.Flags.Type.BROADCAST, False, 3, 2)
        assert msg1 == msg3

        msg4 = Msg.Flags(Msg.Flags.Type.BROADCAST, True)
        assert msg1 != msg4

        msg5 = Msg.Flags(Msg.Flags.Type.DIRECT, False)
        assert msg1 != msg5

    #-----------------------------------------------------------------------
    def test_hops(self):
        obj = Msg.Flags(Msg.Flags.Type.DIRECT, False, 2, 3)
        assert obj.hops_left == 2
        assert obj.max_hops == 3

        obj.set_hops(1)
        assert obj.hops_left == 1
        assert obj.max_hops == 1

    #-----------------------------------------------------------------------
