#===========================================================================
#
# Tests for: insteont_mqtt/message/DbFlags.py
#
#===========================================================================
import insteon_mqtt.message as Msg


class Test_DbFlags:
    #-----------------------------------------------------------------------
    def check(self, obj, in_use, is_ctrl, is_last_rec, raw):
        assert obj.in_use == in_use
        assert obj.is_controller == is_ctrl
        assert obj.is_last_rec == is_last_rec

        out = obj.to_bytes()
        assert len(out) == 1
        assert out[0] == raw

        d = obj.to_json()
        obj2 = Msg.DbFlags.from_json(d)
        assert obj2.in_use == in_use
        assert obj2.is_controller == is_ctrl
        assert obj2.is_last_rec == is_last_rec

        str(obj)

    #-----------------------------------------------------------------------
    def test_basic(self):
        use_ctrl_high = 0b11100010
        use_ctrl_low = 0b11100000
        use_resp_high = 0b10100010
        free_ctrl_high = 0b01100010
        free_ctrl_low = 0b01100000
        free_resp_high = 0b00100010

        b = bytes([use_ctrl_high, use_ctrl_low, use_resp_high,
                   free_ctrl_high, free_ctrl_low, free_resp_high])
        in_use = [1, 1, 1, 0, 0, 0]
        is_ctrl = [1, 1, 0, 1, 1, 0]
        is_high = [1, 0, 1, 1, 0, 1]

        for i in range(len(b)):
            obj = Msg.DbFlags.from_bytes(b, i)
            self.check(obj, in_use[i], is_ctrl[i], not is_high[i], b[i])

    #-----------------------------------------------------------------------
    def test_copy(self):
        obj = Msg.DbFlags(1, 2, 3)
        obj2 = obj.copy()
        assert obj.in_use == obj2.in_use
        assert obj.is_controller == obj2.is_controller
        assert obj.is_last_rec == obj2.is_last_rec

    #-----------------------------------------------------------------------
