#===========================================================================
#
# MQTT PLM modem device
#
#===========================================================================
from .. import log
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class Modem:
    """TODO: doc
    """
    def __init__(self, mqtt, modem):
        """TODO: doc
        """
        self.mqtt = mqtt
        self.device = modem

        # Input scene on/off command template.
        self.msg_scene = MsgTemplate(
            topic='insteon/modem/scene',
            payload='{{value}}',
            )

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['switch'].
          qos:      The default quality of service level to use.
        """
        data = config.get("modem", None)
        if not data:
            return

        self.msg_scene.load_config(config, 'scene_topic', 'scene_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Args:
          link:   The MQTT network client to use.
          qos:    The quality of service to use.
        """
        topic = self.msg_scene.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_scene)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link:   The MQTT network client to use.
        """
        topic = self.msg_scene.render_topic(self.template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def template_data(self):
        """TODO: doc
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name,
            }
        return data

    #-----------------------------------------------------------------------
    def handle_scene(self, client, data, message):
        """TODO: doc
        """
        LOG.debug("Modem message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_scene.to_json(message.payload)
        LOG.info("Modem input command: %s", data)

        try:
            cmd = data.get('cmd')
            if cmd == 'on':
                is_on = True
            elif cmd == 'off':
                is_on = False
            else:
                raise Exception("Invalid modem cmd input '%s'" % cmd)

            group = int(data.get('group', None))
        except:
            LOG.exception("Invalid modem command: %s", data)
            return

        # Tell the device to trigger the scene command.
        self.device.scene(is_on, group)

    #-----------------------------------------------------------------------
