#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/Reply.py
#
#===========================================================================
import insteon_mqtt.mqtt as IMM


class Test_Reply:
    #-----------------------------------------------------------------------
    def test_end(self):
        type = IMM.Reply.Type.END
        data = "foo bar"
        obj = IMM.Reply(type, data)

        assert obj.type == type
        assert obj.data == data

        d = obj.to_json()
        obj2 = IMM.Reply.from_json(d)
        assert obj2.type == type
        assert obj2.data == data

    #-----------------------------------------------------------------------
    def test_message(self):
        type = IMM.Reply.Type.MESSAGE
        data = "foo bar"
        obj = IMM.Reply(type, data)

        assert obj.type == type
        assert obj.data == data

        d = obj.to_json()
        obj2 = IMM.Reply.from_json(d)
        assert obj2.type == type
        assert obj2.data == data

    #-----------------------------------------------------------------------
    def test_error(self):
        type = IMM.Reply.Type.ERROR
        data = "foo bar"
        obj = IMM.Reply(type, data)

        assert obj.type == type
        assert obj.data == data

        d = obj.to_json()
        obj2 = IMM.Reply.from_json(d)
        assert obj2.type == type
        assert obj2.data == data
