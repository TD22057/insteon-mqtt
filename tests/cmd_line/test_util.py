#===========================================================================
#
# Tests for: insteont_mqtt/cmd_line/util.py
#
#===========================================================================
import insteon_mqtt as IM


class Test_util:
    def test_callback_msg(self, capsys):
        text = "message text"
        reply = IM.mqtt.Reply(IM.mqtt.Reply.Type.MESSAGE, text)
        json = reply.to_json()

        message = MockMessage("dummy", json)

        session = {
            "quiet" : False,
            "done" : False,
            "status" : 0,
            "end_time" : 0,
            }
        client = None
        IM.cmd_line.util.callback(client, session, message)
        assert session["done"] is False
        assert session["status"] == 0
        assert session["end_time"] > 0

        out, _err = capsys.readouterr()
        assert out == text + "\n"

    #-----------------------------------------------------------------------
    def test_callback_end(self, capsys):
        reply = IM.mqtt.Reply(IM.mqtt.Reply.Type.END, None)
        json = reply.to_json()

        message = MockMessage("dummy", json)

        session = {
            "quiet" : False,
            "done" : False,
            "status" : 0,
            "end_time" : 0,
            }
        client = None
        IM.cmd_line.util.callback(client, session, message)
        assert session["done"] is True
        assert session["status"] == 0
        assert session["end_time"] > 0

    #-----------------------------------------------------------------------
    def test_callback_error(self, capsys):
        text = "message text"
        reply = IM.mqtt.Reply(IM.mqtt.Reply.Type.ERROR, text)
        json = reply.to_json()

        message = MockMessage("dummy", json)

        session = {
            "quiet" : False,
            "done" : False,
            "status" : 0,
            "end_time" : 0,
            }
        client = None
        IM.cmd_line.util.callback(client, session, message)
        assert session["done"] is False
        assert session["status"] == -1
        assert session["end_time"] > 0

        out, _err = capsys.readouterr()
        assert "ERROR" in out
        assert text in out

    #-----------------------------------------------------------------------


#===========================================================================
class MockMessage:
    def __init__(self, topic, msg):
        self.topic = topic
        self.payload = msg.encode("utf-8")
