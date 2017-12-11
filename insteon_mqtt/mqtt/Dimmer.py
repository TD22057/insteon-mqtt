#===========================================================================
#
# MQTT dimmer switch device
#
#===========================================================================
from .. import log
from .MsgTemplate import MsgTemplate
from .Switch import Switch

LOG = log.get_logger()


class Dimmer(Switch):
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        super().__init__(mqtt, device, handle_active=False)

        # Output state change reporting template.
        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state',
            payload='{ "state" : "{{on_str.upper()}}", '
                    '"brightness" : {{level_255}} }',
            )

        # Input level command template.
        self.msg_level = MsgTemplate(
            topic='insteon/{{address}}/level',
            payload='{ "cmd" : "{{json.state.lower()}}", '
                    '"level" : {{json.brightness}} }',
            )

        device.signal_level_changed.connect(self.handle_level_changed)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """TODO: doc
        """
        data = config.get("dimmer", None)
        super().load_switch_config(data, qos)
        self.load_dimmer_config(data, qos)

    #-----------------------------------------------------------------------
    def load_dimmer_config(self, config, qos):
        """TODO: doc
        """
        if not config:
            return

        # The Switch base class will load the msg_state template for us.
        self.msg_level.load_config(config, 'level_topic', 'level_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """TODO: doc
        """
        super().subscribe(link, qos)

        topic = self.msg_level.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_set_level)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """TODO: doc
        """
        super().unsubscribe(link)

        topic = self.msg_level.render_topic(self.template_data())
        self.mqtt.unsubscribe(topic)

    #-----------------------------------------------------------------------
    # pylint: disable=arguments-differ
    def template_data(self, level=None):
        """TODO: doc
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            }

        if level is not None:
            data["on"] = 1 if level else 0,
            data["on_str"] = "on" if level else "off"
            data["level_255"] = level
            data["level_100"] = int(100.0 * level / 255.0)

        return data

    #-----------------------------------------------------------------------
    def handle_level_changed(self, device, level):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          level     (int) True for on, False for off.
        """
        LOG.info("MQTT received level change %s '%s' = %s",
                 device.addr, device.name, level)

        data = self.template_data(level)
        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_set_level(self, client, data, message):
        """TODO: doc
        """
        LOG.info("Dimmer message %s %s", message.topic, message.payload)

        data = self.msg_level.to_json(message.payload)
        if not data:
            return

        LOG.info("Dimmer input command: %s", data)
        try:
            cmd = data.get('cmd')
            if cmd == 'on':
                level = int(data.get('level'))
            elif cmd == 'off':
                level = 0
            else:
                raise Exception("Invalid dimmer cmd input '%s'" % cmd)

            instant = bool(data.get('instant', False))
        except:
            LOG.exception("Invalid dimmer command: %s", data)
            return

        self.device.set(level, instant)

    #-----------------------------------------------------------------------
