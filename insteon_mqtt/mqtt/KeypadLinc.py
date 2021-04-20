#===========================================================================
#
# MQTT keypad linc with 4 or 8 button
#
#===========================================================================
from .. import log
from . import topic
from ..device.base import DimmerBase

LOG = log.get_logger()


class KeypadLinc(topic.SetTopic, topic.SceneTopic, topic.StateTopic,
                 topic.ManualTopic, topic.DiscoveryTopic):
    """MQTT interface to an Insteon KeypadLinc switch.

    This class connects to a device.KeypadLinc object and converts it's output
    state changes to MQTT messages.  It also subscribes to topics to allow
    input MQTT messages to change the state of the Insteon device.
    """
    def __init__(self, mqtt, device, **kwargs):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.KeypadLinc):  The Insteon object to link to.
          kwargs (dict):  Additional settings from the KPL Dimmer
        """
        super().__init__(mqtt, device,
                         scene_topic='insteon/{{address}}/scene/{{button}}',
                         state_topic='insteon/{{address}}/state/{{button}}',
                         set_topic='insteon/{{address}}/set/{{button}}',
                         **kwargs)

        # This defines the default discovery_class for these devices
        self.default_discovery_cls = "keypad_linc"

        # Set the groups for discovery topic generation
        self.extra_topic_nums = range(1, 10)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['keypad_linc'].
          qos (int):  The default quality of service level to use.
        """
        # The discovery topic needs the full config
        self.load_discovery_data(config, qos)

        data = config.get("keypad_linc", None)
        if not data:
            return

        # Load the various topics
        self.load_state_data(data, qos,
                             topic='btn_state_topic',
                             payload='btn_state_payload',
                             topic_1='dimmer_state_topic',
                             payload_1='dimmer_state_payload')
        self.load_manual_data(data, qos)
        self.load_scene_data(data, qos,
                             topic='btn_scene_topic',
                             payload='btn_scene_payload')

        self.load_set_data(data, qos,
                           topic='btn_on_off_topic',
                           payload='btn_on_off_payload')

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos, start_group=1):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        # We need to subscribe to each button topic so we know which one is
        # which.
        for group in range(start_group, 9):
            self.set_subscribe(link, qos, group=group)
            self.scene_subscribe(link, qos, group=group)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        for group in range(1, 9):
            self.set_unsubscribe(link, group=group)
            self.scene_unsubscribe(link, group=group)

    #-----------------------------------------------------------------------
    def discovery_template_data(self, **kwargs):
        """Create the Jinja templating data variables for discovery messages.

        This extends the default dict with additional variables supported
        by this device

        Returns:
          dict:  Returns a dict with the variables available for templating.
                 including:
        """
        # Get the default variables
        data = super().discovery_template_data(**kwargs)  # pylint:disable=E1101
        data['is_dimmable'] = False
        if isinstance(self.device, DimmerBase):
            data['is_dimmable'] = True
        return data

        #-----------------------------------------------------------------------
