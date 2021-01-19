#===========================================================================
#
# EZIO4O 4 relay output device
#
#===========================================================================
from .. import log
from . import topic

LOG = log.get_logger()


class EZIO4O(topic.StateTopic, topic.SetTopic):
    """MQTT interface to Smartenit EZIO4O 4 relay output device.

    This class connects to a device.EZIO4O object and converts it's
    output state changes to MQTT messages.  It also subscribes to topics to
    allow input MQTT messages to change the state of the device.

    EZIO4O will report their state (state/output) and can be commanded to turn
    on and off (set/output topic).
    """

    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Outlet):  The Insteon object to link to.
        """
        # Setup the Topics
        super().__init__(mqtt, device,
                         state_topic='insteon/{{address}}/state/{{button}}',
                         set_topic="insteon/{{address}}/set/{{button}}")

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from. The object
                 config is stored in config['ezio4o'].
          qos (int):  The default quality of service level to use.
        """
        data = config.get("ezio4o", None)
        if not data:
            return

        # Load the various topics
        self.load_state_data(data, qos)
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
        # Connect input topics for groups 1 to 4 (one for each relay).
        # Create a function that will call the input callback with the right
        # group number set for each socket.
        for group in [1, 2, 3, 4]:
            self.set_subscribe(link, qos, group=group)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        for group in [1, 2, 3, 4]:
            self.set_unsubscribe(link, group=group)

    #-----------------------------------------------------------------------
