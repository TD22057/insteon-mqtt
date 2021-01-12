#===========================================================================
#
# MQTT On/Off switch device
#
#===========================================================================
from .. import log
from . import topic

LOG = log.get_logger()


class Switch(topic.SetTopic, topic.StateTopic, topic.SceneTopic,
             topic.ManualTopic):
    """MQTT interface to an Insteon on/off switch.

    This class connects to a device.Switch object and converts it's
    output state changes to MQTT messages.  It also subscribes to topics to
    allow input MQTT messages to change the state of the Insteon device.

    Switches will report their state and can be commanded to turn on and off.
    """

    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Switch):  The Insteon object to link to.
        """
        # Setup the Topics
        super().__init__(mqtt, device)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['switch'].
          qos (int):  The default quality of service level to use.
        """
        data = config.get("switch", None)
        if not data:
            return

        # Load the various topics
        self.load_scene_data(data, qos)
        self.load_state_data(data, qos)
        self.load_manual_data(data, qos)
        self.load_set_data(data, qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        # On/off command messages.
        self.set_subscribe(link, qos)
        self.scene_subscribe(link, qos)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        self.set_unsubscribe(link)
        self.scene_unsubscribe(link)

    #-----------------------------------------------------------------------
