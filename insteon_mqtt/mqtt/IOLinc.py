#===========================================================================
#
# MQTT On/Off switch device
#
#===========================================================================
from .. import log
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class IOLinc:
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        self.mqtt = mqtt
        self.device = device

        # Output state change reporting template.
        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state',
            payload='{{on_str.lower()}}',
            )

        # Input on/off command template.
        self.msg_on_off = MsgTemplate(
            topic='insteon/{{address}}/set',
            payload='{ "cmd" : "{{value.lower()}}" }',
            )

        # Input scene on/off command template.
        self.msg_scene_on_off = MsgTemplate(
            topic='insteon/{{address}}/scene',
            payload='{ "cmd" : "{{value.lower()}}" }',
            )

        device.signal_active.connect(self.handle_active)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['switch'].
          qos:      The default quality of service level to use.
        """
        self.load_switch_config(config.get("io_linc", None), qos)

    #-----------------------------------------------------------------------
    def load_switch_config(self, config, qos):
        """TODO: doc
        """
        if not config:
            return

        self.msg_state.load_config(config, 'state_topic', 'state_payload', qos)
        self.msg_on_off.load_config(config, 'on_off_topic', 'on_off_payload',
                                    qos)
        self.msg_scene_on_off.load_config(config, 'scene_on_off_topic',
                                          'scene_on_off_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Args:
          link:   The MQTT network client to use.
          qos:    The quality of service to use.
        """
        topic = self.msg_on_off.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_set)

        topic = self.msg_scene_on_off.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_scene)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link:   The MQTT network client to use.
        """
        topic = self.msg_on_off.render_topic(self.template_data())
        link.unsubscribe(topic)

        topic = self.msg_scene_on_off.render_topic(self.template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def template_data(self, is_active=None):
        """TODO: doc
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            }

        if is_active is not None:
            data["on"] = 1 if is_active else 0
            data["on_str"] = "on" if is_active else "off"

        return data

    #-----------------------------------------------------------------------
    def handle_active(self, device, is_active):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_active (bool) True for on, False for off.
        """
        LOG.info("MQTT received active change %s = %s", device.label,
                 is_active)

        data = self.template_data(is_active)
        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_set(self, client, data, message):
        """TODO: doc
        """
        LOG.debug("IOLinc message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_on_off.to_json(message.payload)
        LOG.info("IOLinc input command: %s", data)

        try:
            cmd = data.get('cmd')
            if cmd == 'on':
                is_on = True
            elif cmd == 'off':
                is_on = False
            else:
                raise Exception("Invalid switch cmd input '%s'" % cmd)

        except:
            LOG.exception("Invalid switch command: %s", data)
            return

        # Tell the device to update it's state.
        self.device.set(is_on)

    #-----------------------------------------------------------------------
    def handle_scene(self, client, data, message):
        """TODO: doc
        """
        LOG.debug("IOLinc message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_scene_on_off.to_json(message.payload)
        LOG.info("IOLinc input command: %s", data)

        try:
            cmd = data.get('cmd')
            if cmd == 'on':
                is_on = True
            elif cmd == 'off':
                is_on = False
            else:
                raise Exception("Invalid switch cmd input '%s'" % cmd)

        except:
            LOG.exception("Invalid switch command: %s", data)
            return

        # Tell the device to trigger the scene command.
        self.device.scene(is_on)

    #-----------------------------------------------------------------------
