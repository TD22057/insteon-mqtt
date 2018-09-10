#===========================================================================
#
# MQTT dimmer switch device
#
#===========================================================================
from .. import log
from .. import device as Dev
from .Dimmer import Dimmer
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class FanLinc(Dimmer):
    """TODO: doc
    """
    level_map = {
        Dev.FanLinc.Speed.OFF : (0, "off"),
        Dev.FanLinc.Speed.LOW : (1, "low"),
        Dev.FanLinc.Speed.MED : (2, "medium"),
        Dev.FanLinc.Speed.HIGH : (3, "high"),
        }
    cmd_map = {
        "off" : Dev.FanLinc.Speed.OFF,
        "low" : Dev.FanLinc.Speed.LOW,
        "medium" : Dev.FanLinc.Speed.MED,
        "high" : Dev.FanLinc.Speed.HIGH,
        "on" : Dev.FanLinc.Speed.ON,
        }

    def __init__(self, mqtt, device):
        """TODO: doc
        """
        super().__init__(mqtt, device)

        # Output fan state change reporting template.
        self.msg_fan_state = MsgTemplate(
            topic='insteon/{{address}}/fan/state',
            payload='{{level_str}}',
            )

        # Input fan on/off command template.
        self.msg_fan_on_off = MsgTemplate(
            topic='insteon/{{address}}/set',
            payload='{ "cmd" : "{{value.lower()}}" }',
            )

        # Output fan speed state change reporting template.  Default
        # is to report speeds via the state topic.
        self.msg_fan_speed_state = MsgTemplate(topic='', payload='')

        # Input fan speed level command template.
        self.msg_fan_speed = MsgTemplate(topic='', payload='')

        device.signal_fan_changed.connect(self.handle_fan_changed)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['fan_linc'].
          qos:      The default quality of service level to use.
        """
        # Load the dimmer configuration from the dimmer area, not the
        # fanlinc area.
        super().load_config(config, qos)

        # Now load the fan control configuration
        data = config.get("fan_linc", None)
        self.load_fanlinc_config(data, qos)

    #-----------------------------------------------------------------------
    def load_fanlinc_config(self, config, qos=None):
        """TODO: doc
        """
        if not config:
            return

        self.msg_fan_state.load_config(config, 'fan_state_topic',
                                       'fan_state_payload', qos)
        self.msg_fan_on_off.load_config(config, 'fan_on_off_topic',
                                        'fan_on_off_payload', qos)
        self.msg_fan_speed_state.load_config(config, 'fan_speed_topic',
                                             'fan_speed_payload', qos)
        self.msg_fan_speed.load_config(config, 'fan_speed_set_topic',
                                       'fan_speed_set_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Args:
          link:   The MQTT network client to use.
          qos:    The quality of service to use.
        """
        super().subscribe(link, qos)

        data = self.fan_template_data()

        topic = self.msg_fan_on_off.render_topic(data)
        if topic:
            link.subscribe(topic, qos, self.handle_set_fan_speed)

        topic = self.msg_fan_speed.render_topic(data)
        if topic:
            link.subscribe(topic, qos, self.handle_set_fan_speed)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link:   The MQTT network client to use.
        """
        super().unsubscribe(link)

        data = self.fan_template_data()

        topic = self.msg_fan_on_off.render_topic(data)
        if topic:
            link.unsubscribe(topic)

        topic = self.msg_fan_speed.render_topic(data)
        if topic:
            link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    # pylint: disable=arguments-differ
    def fan_template_data(self, level=None):
        """TODO: doc
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            }

        if level is not None:
            level_int, level_str = FanLinc.level_map[level]

            data["on"] = 1 if level_int else 0
            data["on_str"] = "on" if level_int else "off"
            data["level"] = level_int
            data["level_str"] = level_str

        return data

    #-----------------------------------------------------------------------
    def handle_fan_changed(self, device, level):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          level     (device.FanLinc.Speed) The new fan level.
        """
        LOG.info("MQTT received level change %s = %s", device.label, level)

        data = self.fan_template_data(level)
        self.msg_fan_state.publish(self.mqtt, data)
        self.msg_fan_speed_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_set_fan_speed(self, client, data, message):
        """TODO: doc
        """
        LOG.info("FanLink fan on/off message %s %s", message.topic,
                 message.payload)

        data = self.msg_fan_on_off.to_json(message.payload)
        if not data:
            return

        LOG.info("FanLink fan on/off input command: %s", data)
        try:
            cmd = data.get('cmd', None)
            fan_speed = FanLinc.cmd_map.get(cmd, None)
            if fan_speed is None:
                raise ValueError("Can't map cmd to fan mode")

            self.device.fan_set(fan_speed)
        except:
            LOG.error("Invalid fan set cmd '%s'", cmd)

    #-----------------------------------------------------------------------
