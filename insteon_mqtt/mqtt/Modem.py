#===========================================================================
#
# MQTT PLM modem device
#
#===========================================================================
from .. import log
from .MsgTemplate import MsgTemplate
from . import util

LOG = log.get_logger()


class Modem:
    """MQTT interface to an Insteon power line modem (PLM).

    This class connects to an insteon_mqtt.Modem object and allows input MQTT
    messages to be converted and sent to the modem to simulate scene
    (activate modem scenes).
    """
    def __init__(self, mqtt, modem):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          modem (Modem):  The Insteon modem object to link to.
        """
        self.mqtt = mqtt
        self.device = modem

        # Input scene on/off command template.
        self.msg_scene = MsgTemplate(
            topic='insteon/modem/scene',
            payload='{{value}}')

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['modem'].
          qos (int):  The default quality of service level to use.
        """
        data = config.get("modem", None)
        if not data:
            return

        self.msg_scene.load_config(data, 'scene_topic', 'scene_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        topic = self.msg_scene.render_topic(self.template_data())
        link.subscribe(topic, qos, self._input_scene)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        topic = self.msg_scene.render_topic(self.template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def template_data(self):
        """Create the Jinja templating data variables for messages.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name,
            }
        return data

    #-----------------------------------------------------------------------
    def _input_scene(self, client, data, message):
        """Handle an input simulate scene MQTT message.

        This is called when we receive a message on the scene change MQTT
        topic subscription.  Parse the message and pass the command to the
        Insteon device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.debug("Modem message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_scene.to_json(message.payload)
        LOG.info("Modem input command: %s", data)

        try:
            is_on = util.parse_on_off(data, have_mode=False)
            group = int(data.get('group', None)) if 'group' in data else None
            name = str(data.get('name', None)) if 'name' in data else None

            # Tell the device to trigger the scene command.
            self.device.scene(is_on, group=group, name=name)
        except:
            LOG.exception("Invalid modem command: %s", data)

    #-----------------------------------------------------------------------
