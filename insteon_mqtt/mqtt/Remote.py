#===========================================================================
#
# MQTT Mini-remote battery powered remote control.
#
#===========================================================================
from .. import log
from .BatterySensor import BatterySensor
from . import topic

LOG = log.get_logger()


class Remote(BatterySensor, topic.ManualTopic):
    """MQTT interface to an Insteon mini-remote.

    This class connects to a device.Remote object and converts it's output
    state changes to MQTT messages.

    Remotes report button presses on the remote control.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Remote):  The Insteon object to link to.
        """
        super().__init__(mqtt, device,
                         state_topic='insteon/{{address}}/state/{{button}}',
                         state_payload='{{on_str.lower()}}')
        # For the remote control, there is no way to know it's state on start
        # up so we don't want to retain those messages.  If we did, then a
        # remote that got out of sync (because of the device changing state
        # and the remote not knowing about it) would cause problems when HA
        # is restarted because the remotes retain message would still be in
        # the broker.
        # I am not sure I understand the rational here, we retain messages
        # from other battery devices such as motion sensors.  Isn't it up to
        # the subscriber of the topic to determine if it should act on a
        # retained message? - KRKeegan 2021-01-10
        self.state_retain = False

        # This defines the default discovery_class for these devices
        self.class_name = "remote"

        # Set the groups for discovery topic generation
        self.group_topic_nums = range(1, 9)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['remote'].
          qos (int):  The default quality of service level to use.
        """
        super().load_config(config, qos)

        data = config.get("remote", None)
        if not data:
            return

        # Load the various topics
        self.load_state_data(data, qos)
        self.load_manual_data(data, qos)

        # Leak and Motion allow for overrides b/c of grandfathering.  But I
        # think is may be a helpful feature, so enabling here too.
        if "low_battery_topic" in data:
            self.msg_battery.load_config(data, 'low_battery_topic',
                                         'low_battery_payload', qos)

    #-----------------------------------------------------------------------
    def discovery_template_data(self, **kwargs):
        """This extends the template data variables defined in the base class

        Adds the state_topics
        """
        # Set up the variables that can be used in the templates.
        data = super().discovery_template_data(**kwargs)  # pylint:disable=E1101
        if 'state_topic' in data:
            data['wet_dry_topic'] = data.pop('state_topic')
        return data

    #-----------------------------------------------------------------------
