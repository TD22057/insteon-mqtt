#===========================================================================
#
# Tests for: insteont_mqtt/cmd_line/modem.py
#
#===========================================================================
import insteon_mqtt as IM


class Data:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class Test_modem:
    def check_call(self, func, args, config, topic, cmd):
        call = func.call_args[0]
        assert call[0] == config
        assert call[1] == topic
        assert call[2]["cmd"] == cmd
        assert call[2]["force"] == args.force
        assert call[3] == args.quiet

    #-----------------------------------------------------------------------
    def test_refresh_all(self, mocker):
        mocker.patch('insteon_mqtt.cmd_line.util.send')
        IM.cmd_line.util.send.return_value = {"status" : 10}

        args = Data(topic="cmd_topic", force=False, quiet=True)
        config = Data(a=1, b=2)

        r = IM.cmd_line.modem.refresh_all(args, config)
        assert r == 10

        self.check_call(IM.cmd_line.util.send, args, config, "cmd_topic/modem",
                        "refresh_all")

    #-----------------------------------------------------------------------
