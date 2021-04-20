#===========================================================================
#
# MQTT battery sensor device
#
#===========================================================================
import time
from .. import log
from .MsgTemplate import MsgTemplate
from . import topic

LOG = log.get_logger()


class BatterySensor(topic.StateTopic, topic.DiscoveryTopic):
    """MQTT interface to an Insteon general battery powered sensor.

    This class connects to a device.BatterySensor object and converts it's
    output state changes to MQTT messages.

    Battery sensors don't support any input commands - they're sleeping until
    activated so they can't respond to commands.  Battery sensors have a
    state topic and a low battery topic they will publish to.
    """
    def __init__(self, mqtt, device, **kwargs):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.BatterySensor):  The Insteon object to link to.
        """
        # Setup the Topics
        super().__init__(mqtt, device, **kwargs)

        # Default values for the topics.
        self.msg_battery = MsgTemplate(
            topic='insteon/{{address}}/battery',
            payload='{{is_low_str.lower()}}')
        self.msg_heartbeat = MsgTemplate(
            topic='insteon/{{address}}/heartbeat',
            payload='{{heartbeat_time}}')

        # Connect the signals from the insteon device so we get notified of
        # changes.
        device.signal_low_battery.connect(self._insteon_low_battery)
        device.signal_heartbeat.connect(self._insteon_heartbeat)

        # This defines the default discovery_class for these devices
        self.default_discovery_cls = "battery_sensor"

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['battery_sensor'].
          qos (int):  The default quality of service level to use.
        """
        # The discovery topic needs the full config
        self.load_discovery_data(config, qos)

        data = config.get("battery_sensor", None)
        if not data:
            return

        # Load the various topics
        self.load_state_data(data, qos)

        self.msg_battery.load_config(data, 'low_battery_topic',
                                     'low_battery_payload', qos)
        self.msg_heartbeat.load_config(data, 'heartbeat_topic',
                                       'heartbeat_payload', qos)

        # Add our unique topics to the discovery topic map
        topics = {}
        var_data = self.base_template_data()
        topics['low_battery_topic'] = self.msg_battery.render_topic(var_data)
        topics['heartbeat_topic'] = self.msg_heartbeat.render_topic(var_data)
        self.rendered_topic_map.update(topics)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        # There are no input controls for this object so we don't need to
        # subscribe to anything.
        pass

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        pass

    #-----------------------------------------------------------------------
    def template_data(self, is_on=None, is_low=None, is_heartbeat=None):
        """Create the Jinja templating data variables.

        Args:
          is_on (bool):  Is the device on or off.  If this is None, on/off
                attributes are not added to the data.
          is_low (bool):  Is the device low battery or not.  If this is None,
                 low battery attributes are not added to the data.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        # Set up the variables that can be used in the templates.
        data = self.base_template_data()

        if is_on is not None:
            data["on"] = 1 if is_on else 0
            data["on_str"] = "on" if is_on else "off"

        if is_low is not None:
            data["is_low"] = 1 if is_low else 0
            data["is_low_str"] = "on" if is_low else "off"

        if is_heartbeat is not None:
            data["is_heartbeat"] = 1 if is_heartbeat else 0
            data["is_heartbeat_str"] = "on" if is_heartbeat else "off"
            data["heartbeat_time"] = time.time() if is_heartbeat else 0

        return data

    #-----------------------------------------------------------------------
    def _insteon_low_battery(self, device, is_low):
        """Device low battery on/off callback.

        This is triggered via signal when the Insteon device detects a low
        batter.  It will publish an MQTT message with the new state.

        Args:
          device (device.BatterySensor):  The Insteon device that changed.
          is_low (bool):  True for low battery, False for not.
        """
        LOG.info("MQTT received low battery %s low: %s", device.label, is_low)

        data = self.template_data(is_low=is_low)
        self.msg_battery.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _insteon_heartbeat(self, device, is_heartbeat):
        """Device heartbeat on/off callback.

        This is triggered via signal when the Insteon device receive a
        heartbeat. It will publish an MQTT message with the new date.

        Args:
          device (device.Leak):  The Insteon device that changed.
          is_heartbeat (bool):  True for heartbeat, False for not.
        """
        LOG.info("MQTT received heartbeat %s = %s", device.label,
                 is_heartbeat)

        data = self.template_data(is_heartbeat=is_heartbeat)
        self.msg_heartbeat.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
