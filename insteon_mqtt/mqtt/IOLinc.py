#===========================================================================
#
# MQTT On/Off switch device
#
#===========================================================================
from .. import log
from .MsgTemplate import MsgTemplate
from . import topic

LOG = log.get_logger()


class IOLinc(topic.StateTopic, topic.SetTopic, topic.DiscoveryTopic):
    """MQTT interface to an Insteon IOLinc device.

    This class connects to a device.IOLinc object and converts it's
    output state changes to MQTT messages.  It also subscribes to topics to
    allow input MQTT messages to change the state of the Insteon device.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.IOLinc):  The Insteon object to link to.
        """
        super().__init__(mqtt, device,
                         state_payload='{"sensor":"{{sensor_on_str.lower()}}",'
                                       ' "relay":"{{relay_on_str.lower()}}"}')

        # Output relay state change reporting template.
        self.msg_relay_state = MsgTemplate(
            topic='insteon/{{address}}/relay',
            payload='{{relay_on_str.lower()}}')

        # Output sensor state change reporting template.
        self.msg_sensor_state = MsgTemplate(
            topic='insteon/{{address}}/sensor',
            payload='{{sensor_on_str.lower()}}')

        device.signal_state.connect(self._insteon_on_off)

        # This defines the default discovery_class for these devices
        self.default_discovery_cls = "io_linc"

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['io_linc'].
          qos (int):  The default quality of service level to use.
        """
        # The discovery topic needs the full config
        self.load_discovery_data(config, qos)

        data = config.get("io_linc", None)
        if not data:
            return

        self.load_state_data(data, qos)
        self.msg_relay_state.load_config(data, 'relay_state_topic',
                                         'relay_state_payload', qos)
        self.msg_sensor_state.load_config(data, 'sensor_state_topic',
                                          'sensor_state_payload', qos)
        self.load_set_data(data, qos)

        # Add our unique topics to the discovery topic map
        topics = {}
        var_data = self.base_template_data()
        topics['relay_state_topic'] = self.msg_relay_state.render_topic(
            var_data
        )
        topics['sensor_state_topic'] = self.msg_sensor_state.render_topic(
            var_data
        )
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
        # On/off command messages.
        self.set_subscribe(link, qos)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        self.set_unsubscribe(link)

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

        button = kwargs.get('button', None)
        # Handle_Refresh sends level and not is_on
        is_on = kwargs.get('is_on', None)
        level = kwargs.get('level', 0x00)
        if is_on is None:
            is_on = level > 0
        if button is not None:
            # I am not very happy about having to query back to the device
            # here.  But this is needed because when first designing this
            # class I allowed a state topic that produced the states of two
            # things, the sensor and the relay.  Had these been kept in
            # different topics this would not be needed.  Consider that if
            # copying this code.
            if button == 1:  # This was a sensor emit
                sensor_is_on = is_on
                relay_is_on = self.device.relay_is_on
            elif button == 2:  # This was a relay emit
                relay_is_on = is_on
                sensor_is_on = self.device.sensor_is_on

            data["sensor_on"] = 1 if sensor_is_on else 0
            data["sensor_on_str"] = "on" if sensor_is_on else "off"
            data["relay_on"] = 1 if relay_is_on else 0
            data["relay_on_str"] = "on" if relay_is_on else "off"
        return data

    #-----------------------------------------------------------------------
    def _insteon_on_off(self, device, **kwargs):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes active or
        inactive.  It will publish an MQTT message with the new state.

        Args:
          device (device.IOLinc):   The Insteon device that changed.
          is_on (bool):   True for on, False for off.
        """
        LOG.info("MQTT received active change %s, %s",
                 device.label, kwargs)

        data = self.state_template_data(**kwargs)
        self.msg_relay_state.publish(self.mqtt, data)
        self.msg_sensor_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
