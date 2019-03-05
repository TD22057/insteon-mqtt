#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/MsgTemplate.py
#
#===========================================================================
import helpers as H
import insteon_mqtt as IM
from insteon_mqtt.mqtt import MsgTemplate


class Test_MsgTemplate:
    #-----------------------------------------------------------------------
    def test_clean(self):
        topic = "  ka j sd fja   "
        right = "ka j sd fja"
        assert MsgTemplate.clean_topic(topic) == right

        assert MsgTemplate.clean_topic(topic + "/") == right

    #-----------------------------------------------------------------------
    def test_null(self):
        msg = MsgTemplate(None, None)
        data = {"foo" : 1, "bar" : 2}

        t = msg.render_topic(data)
        assert t is None

        t = msg.render_payload(data)
        assert t is None

        link = H.network.MockMqtt()
        mqtt = IM.mqtt.Mqtt(link, H.mqtt.MockModem())
        msg.publish(mqtt, data)
        assert len(link.pub) == 0

        data = msg.to_json(b'{ "foo" : 1 }')
        assert data is None

    #-----------------------------------------------------------------------
    def test_render(self):
        topic_templ = '{ "foo"={{foo}}, "bar"={{bar}} }'
        payload_templ = '{ "baz"={{baz}}, "boz"="{{boz}}" }'
        msg = MsgTemplate(topic_templ, payload_templ)

        data = {"foo" : 1, "bar" : 2, "baz" : 3, "boz" : "testing"}
        topic = msg.render_topic(data)
        right = '{ "foo"=1, "bar"=2 }'
        assert topic == right

        payload = msg.render_payload(data)
        right = '{ "baz"=3, "boz"="testing" }'
        assert payload == right

    #-----------------------------------------------------------------------
    def test_publish(self):
        topic_templ = '{ "foo"={{foo}}, "bar"={{bar}} }'
        payload_templ = '{ "baz"={{baz}}, "boz"="{{boz}}" }'
        qos = 2
        retain = True
        msg = MsgTemplate(topic_templ, payload_templ, qos, retain)

        data = {"foo" : 1, "bar" : 2, "baz" : 3, "boz" : "testing"}
        link = H.network.MockMqtt()
        mqtt = IM.mqtt.Mqtt(link, H.mqtt.MockModem())
        msg.publish(mqtt, data)
        assert len(link.pub) == 1

        call = link.pub[0]
        assert call.topic == '{ "foo"=1, "bar"=2 }'
        assert call.payload == '{ "baz"=3, "boz"="testing" }'
        assert call.qos == qos
        assert call.retain == retain

    #-----------------------------------------------------------------------
    def test_load(self):
        config = {
            'abc' : '{ "foo"={{foo}}, "bar"={{bar}} }',
            'def' : '{ "baz"={{baz}}, "boz"="{{boz}}" }',
            }
        qos = 2
        msg = MsgTemplate(None, None)
        msg.load_config(config, 'abc', 'def', qos)

        data = {"foo" : 1, "bar" : 2, "baz" : 3, "boz" : "testing"}
        link = H.network.MockMqtt()
        mqtt = IM.mqtt.Mqtt(link, H.mqtt.MockModem())
        msg.publish(mqtt, data, True)
        assert len(link.pub) == 1

        call = link.pub[0]
        assert call.topic == '{ "foo"=1, "bar"=2 }'
        assert call.payload == '{ "baz"=3, "boz"="testing" }'
        assert call.qos == qos
        assert call.retain is True

    #-----------------------------------------------------------------------
    def test_to_json(self):
        topic_templ = '{ "foo" : {{foo}}, "bar" : {{bar}} }'
        payload_templ = '{ "baz" : {{json.baz}}, "boz" : "{{json.boz}}" }'
        msg = MsgTemplate(topic_templ, payload_templ)

        jdata = msg.to_json(b'{ "baz" : 3, "boz" : "testing" }')
        right = {"baz" : 3, "boz" : "testing"}
        assert jdata == right

    #-----------------------------------------------------------------------
    def test_to_json_error(self, caplog):
        topic_templ = '{ foo = {{foo}}, bar = {{bar}} }'
        payload_templ = '{ baz = {{json.baz}} // boz = {{json.boz}} }'
        msg = MsgTemplate(topic_templ, payload_templ)

        jdata = msg.to_json(b'{ "baz" : 3, "boz" : "testing" }')
        for rec in caplog.records:
            assert rec.levelname == "ERROR"
        assert jdata is None

#===========================================================================
