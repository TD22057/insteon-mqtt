#===========================================================================
#
# MQTT PLM modem device
#
#===========================================================================
from .. import log
from .SceneTopic import SceneTopic
LOG = log.get_logger()


class Modem(SceneTopic):
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
        super().__init__(mqtt, modem, scene_topic='insteon/modem/scene',
                         scene_payload='{ "cmd" : "{{json.cmd.lower()}}",'
                                       '"group" : {{json.group}} }')

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

        self.load_scene_data(data, qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        self.scene_subscribe(link, qos)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        self.scene_unsubscribe(link)

    #-----------------------------------------------------------------------
