#===========================================================================
#
# Tests for: insteont_mqtt/cmd_line/modem.py
#
#===========================================================================
import insteon_mqtt as IM
import helpers


class Test_device:
    def check_call(self, func, args, config, topic, payload):
        call = func.call_args[0]
        assert call[0] == config
        assert call[1] == topic
        assert call[2] == payload
        assert call[3] == args.quiet

    #-----------------------------------------------------------------------
    def test_linking(self, mocker):
        mocker.patch('insteon_mqtt.cmd_line.util.send')
        IM.cmd_line.util.send.return_value = {"status" : 10}

        args = helpers.Data(topic="cmd_topic", force=False, quiet=True,
                            group=5, address="aa.bb.cc")
        config = helpers.Data(a=1, b=2)

        r = IM.cmd_line.device.linking(args, config)
        assert r == 10

        topic = "%s/%s" % (args.topic, args.address)
        payload = {
            "cmd" : "linking",
            "group" : args.group,
            }
        self.check_call(IM.cmd_line.util.send, args, config, topic, payload)

    #-----------------------------------------------------------------------
    def test_set_button_led(self, mocker):
        mocker.patch('insteon_mqtt.cmd_line.util.send')
        IM.cmd_line.util.send.return_value = {"status" : 10}

        args = helpers.Data(topic="cmd_topic", force=False, quiet=True,
                            group=5, address="aa.bb.cc", is_on=True)
        config = helpers.Data(a=1, b=2)

        r = IM.cmd_line.device.set_button_led(args, config)
        assert r == 10

        topic = "%s/%s" % (args.topic, args.address)
        payload = {
            "cmd" : "set_button_led",
            "group" : args.group,
            "is_on" : args.is_on,
            }
        self.check_call(IM.cmd_line.util.send, args, config, topic, payload)

    #-----------------------------------------------------------------------
