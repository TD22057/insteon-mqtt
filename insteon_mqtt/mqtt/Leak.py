#===========================================================================
#
# MQTT leak sensor device
#
#===========================================================================
from .. import log
from .BatterySensor import BatterySensor

LOG = log.get_logger()


class Leak(BatterySensor):
    """Leak battery powered sensor.

    Leak sensors don't support any input commands - they're sleeping until
    activated so they can't respond to commands.  Leak sensors have a state
    topic and a heartbeat topic they will publish to.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Leak):  The Insteon object to link to.
        """
        super().__init__(mqtt, device,
                         state_topic='insteon/{{address}}/wet',
                         state_payload='{{is_wet_str.lower()}}')

        # This defines the default discovery_class for these devices
        self.default_discovery_cls = "leak"

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['leak'].
          qos (int):  The default quality of service level to use.
        """
        # Load the BatterySensor configuration.
        super().load_config(config, qos)

        data = config.get("leak", None)
        if not data:
            return

        # Load the various topics
        self.load_state_data(data, qos, topic='wet_dry_topic',
                             payload='wet_dry_payload')

        # In versions <= 0.7.2, this was in leak sensor so try and
        # load them to insure old config files still work.
        if "heartbeat_topic" in data:
            self.msg_heartbeat.load_config(data, 'heartbeat_topic',
                                           'heartbeat_payload', qos)

        # Add our unique topics to the discovery topic map
        # The state_topic uses a different name on the leak sensor
        if 'state_topic' in self.rendered_topic_map:
            rendered_topic = self.rendered_topic_map.pop('state_topic')
            self.rendered_topic_map['wet_dry_topic'] = rendered_topic

    #-----------------------------------------------------------------------
    def state_template_data(self, **kwargs):
        """Create the Jinja templating data variables for on/off messages.

        kwargs includes:
          is_on (bool):  The on/off state of the switch.  If None, on/off and
                mode attributes are not added to the data.
          mode (on_off.Mode):  The on/off mode state.
          manual (on_off.Manual):  The manual mode state.  If None, manual
                 attributes are not added to the data.
          reason (str):  The reason the device was triggered.  This is an
                 arbitrary string set into the template variables.
          level (int):  A brightness level between 0-255
          button (int): Passed to base_template_data, the group numer to use

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        data = super().state_template_data(**kwargs)

        # Handle_Refresh sends level and not is_on
        is_on = kwargs.get('is_on', None)
        level = kwargs.get('level', 0x00)
        if is_on is None:
            is_on = level > 0

        # Distinguish wet vs dry by the group
        button = kwargs.get('button', None)
        GROUP_WET = 2
        is_wet = False  # Assume dry by default
        # If GROUP_DRY sent the message this will be default to not is_wet
        # already
        if button == GROUP_WET:
            is_wet = is_on

        data["is_wet"] = 1 if is_wet else 0
        data["is_wet_str"] = "on" if is_wet else "off"
        data["is_dry"] = 0 if is_wet else 1
        data["is_dry_str"] = "off" if is_wet else "on"
        data["state"] = "wet" if is_wet else "dry"

        return data

    #-----------------------------------------------------------------------
