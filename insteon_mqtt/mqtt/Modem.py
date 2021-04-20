#===========================================================================
#
# MQTT PLM modem device
#
#===========================================================================
from .. import log
from . import topic
LOG = log.get_logger()


class Modem(topic.SceneTopic, topic.DiscoveryTopic):
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

        # This defines the default discovery_class for these devices
        self.default_discovery_cls = "modem"

        # Set the groups for discovery topic generation
        # self.extra_topic_nums = range(2, 255)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['modem'].
          qos (int):  The default quality of service level to use.
        """
        # The discovery topic needs the full config
        self.load_discovery_data(config, qos)

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
    def publish_discovery(self, **kwargs):
        """This Hijacks the method from DiscoveryTopic

        This is necessary because the Modem is a singular device that requires
        a little different handling to publish the available scenes.

        This is triggered from the MQTT handler.

        No kwargs are currently sent from the MQTT handler, it is a little
        hard to imagine how any such arguments could be provided but left here
        for potential use.

        Args:
          kwargs (dict): The arguments to pass to discovery_template_data
        """
        LOG.info("MQTT received discovery %s on: %s", self.device.label, kwargs)

        data = self.discovery_template_data(**kwargs)

        for scene in self.device.db.groups:
            if scene < 2:
                # Don't publish scenes 0/1, they are not real scenes
                continue
            # Try and load the scene name if it exists
            scene_map = self.device.scene_map
            try:
                scene_index = list(scene_map.values()).index(scene)
                data['scene_name'] = list(scene_map.keys())[scene_index]
            except ValueError:
                # scene does not have a name
                data['scene_name'] = ""
            data['scene'] = scene
            self.entries[0].publish(self.mqtt, data, retain=False)

    #-----------------------------------------------------------------------
