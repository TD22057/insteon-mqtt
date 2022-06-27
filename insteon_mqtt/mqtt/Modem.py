#===========================================================================
#
# MQTT PLM modem device
#
#===========================================================================
import json
import re
from .. import log
from . import topic
from .MsgTemplate import MsgTemplate
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
        data = config.get("modem", None)
        if not data:
            return

        self.load_scene_data(data, qos)

        # Load Discovery Data, Modem uses a slightly different process than
        # all other devices.  It only uses a single template, but needs to
        # pass a variable in the topic
        if not self.mqtt.discovery_enabled:
            return

        class_config = config.get(self.default_discovery_cls, None)
        if class_config is None:
            LOG.error("%s - Unable to find discovery class %s",
                      self.device.label, self.default_discovery_cls)
            return

        # Loop all of the discovery entities and append them to
        # self.rendered_topic_map
        entities = class_config.get('discovery_entities', None)
        if entities is None or not isinstance(entities, dict):
            LOG.error("%s - No discovery_entities defined, or not a dict %s",
                      self.device.label, entities)
            return

        if len(entities) > 1:
            LOG.warning("%s - Modem only uses the first discovery_entity, "
                        "ignoring the rest %s", self.device.label, entities)

        entity = list(entities.values())[0]
        component = entity.get('component', None)
        if component is None:
            LOG.error("%s - No component specified in discovery entity %s",
                      self.device.label, entity)
            return

        payload = entity.get('config', None)
        if payload is None:
            LOG.error("%s - No config specified in discovery entity %s",
                      self.device.label, entity)
            return

        payload = json.dumps(payload, indent=2)
        # replace reference to device_info as string
        # with reference as object (remove quotes)
        payload = re.sub(r'"{{\s*device_info\s*}}"', '{{device_info}}',
                         payload)

        # Get Unique ID from payload to use in topic
        unique_id = self._get_unique_id(payload)
        if unique_id is None:
            LOG.error("%s - Error getting unique_id, skipping entry",
                      self.device.label)
            return

        # HA's implementation of discovery only allows a very limited
        # range of characters in the node_id and object_id fields.
        # See line #30 of /homeassistant/components/mqtt/discovery.py
        # Replace any not-allowed character with underscore
        topic_base = self.mqtt.discovery_topic_base
        address_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', self.device.addr.hex)
        unique_id_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', unique_id)
        default_topic = "%s/%s/%s/%s/config" % (topic_base,
                                                component,
                                                address_safe,
                                                unique_id_safe + "_{{scene}}")
        self.disc_templates.append(MsgTemplate(topic=default_topic,
                                               payload=payload,
                                               qos=qos,
                                               retain=False))

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
        LOG.info("MQTT discovery %s on: %s", self.device.label, kwargs)

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
            self.disc_templates[0].publish(self.mqtt, data.copy(),
                                           retain=False)

    #-----------------------------------------------------------------------
