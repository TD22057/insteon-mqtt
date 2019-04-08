#===========================================================================
#
# MQTT dimmer switch device
#
#===========================================================================
import functools
from .. import log
from .. import device as Dev
from .Dimmer import Dimmer
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class FanLinc(Dimmer):
    """MQTT interface to an Insteon FanLinc switch.

    This class connects to a device.FanLinc object and converts it's output
    state changes to MQTT messages.  A FanLinc is also a dimmer so it has the
    same properties as a dimmer.  Additionally, it reports and can change the
    fan speed.
    """
    # Map of fanlinc levels to MQTT output integer and string values.
    level_map = {
        Dev.FanLinc.Speed.OFF : 0,
        Dev.FanLinc.Speed.LOW : 1,
        Dev.FanLinc.Speed.MEDIUM : 2,
        Dev.FanLinc.Speed.HIGH : 3,
        }

    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.FanLinc):  The Insteon object to link to.
        """
        # Initialize the dimmer.
        super().__init__(mqtt, device)

        # Output fan state change reporting template.
        self.msg_fan_state = MsgTemplate(
            topic='insteon/{{address}}/fan/state',
            payload='{{level_str}}')

        # Input fan on/off command template.
        self.msg_fan_on_off = MsgTemplate(
            topic='insteon/{{address}}/fan/set',
            payload='{ "cmd" : "{{value.lower()}}" }')

        # Output fan speed state change reporting template.  Default is to
        # report speeds via the state topic.
        self.msg_fan_speed_state = MsgTemplate(topic='', payload='')

        # Input fan speed level command template.
        self.msg_fan_speed = MsgTemplate(topic='', payload='')

        device.signal_fan_speed.connect(self._insteon_fan_speed)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['fan_linc'].
          qos (int):  The default quality of service level to use.
        """
        # Load the dimmer configuration from the dimmer area, not the fanlinc
        # area.
        super().load_config(config, qos)

        # Now load the fan control configuration.
        data = config.get("fan_linc", None)
        if not data:
            return

        self.msg_fan_state.load_config(data, 'fan_state_topic',
                                       'fan_state_payload', qos)
        self.msg_fan_on_off.load_config(data, 'fan_on_off_topic',
                                        'fan_on_off_payload', qos)
        self.msg_fan_speed_state.load_config(data, 'fan_speed_topic',
                                             'fan_speed_payload', qos)
        self.msg_fan_speed.load_config(data, 'fan_speed_set_topic',
                                       'fan_speed_set_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        # Subscribe to the dimmer topics.
        super().subscribe(link, qos)

        # Subscribe to the FanLinc topics.
        data = self.template_data()

        topic = self.msg_fan_on_off.render_topic(data)
        if topic:
            handler = functools.partial(self._input_set_fan_speed,
                                        is_speed=False)
            link.subscribe(topic, qos, handler)

        topic = self.msg_fan_speed.render_topic(data)
        if topic:
            handler = functools.partial(self._input_set_fan_speed,
                                        is_speed=True)
            link.subscribe(topic, qos, handler)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        # Unsubscribe from the dimmer topics.
        super().unsubscribe(link)

        data = self.fan_template_data()

        topic = self.msg_fan_on_off.render_topic(data)
        if topic:
            link.unsubscribe(topic)

        topic = self.msg_fan_speed.render_topic(data)
        if topic:
            link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    # pylint: disable=arguments-differ
    def fan_template_data(self, level=None, reason=None):
        """Create the Jinja templating data variables for fan messages.

        NOTE: Dimmer messages are handled via Dimmer.template_data().

        Args:
          level (FanLinc.Speed):  The fan speed enumeration.  If None, speed
                attributes are not added to the data.
          reason (str):  The reason the device was triggered.  This is an
                 arbitrary string set into the template variables.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            }

        if level is not None:
            assert isinstance(level, Dev.FanLinc.Speed)
            level_int = FanLinc.level_map[level]

            data["on"] = 1 if level_int else 0
            data["on_str"] = "on" if level_int else "off"
            data["level"] = level_int
            data["level_str"] = level.name.lower()
            data["reason"] = reason if reason is not None else ""

        return data

    #-----------------------------------------------------------------------
    def _insteon_fan_speed(self, device, level, reason=""):
        """Device speed change callback.

        This is triggered via signal when the Insteon device goes active or
        inactive.  It will publish an MQTT message with the new state.

        Args:
          device (device.FanLinc):  The Insteon device that changed.
          level (device.FanLinc.Speed):  The new fan level.
        """
        LOG.info("MQTT received level change %s = %s %s", device.label, level,
                 reason)

        data = self.fan_template_data(level, reason=reason)
        self.msg_fan_state.publish(self.mqtt, data)
        self.msg_fan_speed_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _input_set_fan_speed(self, client, data, message, is_speed):
        """Handle an input fan speed change MQTT message.

        This is called when we receive a message on the fan speed change MQTT
        topic subscription.  Parse the message and pass the command to the
        Insteon device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
          is_speed: (bool): True to use the speed template, False to use
                    the on/off template.
        """
        LOG.info("FanLink fan on/off message %s %s", message.topic,
                 message.payload)

        if is_speed:
            data = self.msg_fan_speed.to_json(message.payload)
        else:
            data = self.msg_fan_on_off.to_json(message.payload)
        if not data:
            return

        try:
            LOG.info("FanLink fan on/off input command: %s", data)

            # Command will either be on/off or one of the speed enums.  Map
            # the command to a fan linc enumeration.  Commands have the same
            # names as the values in the FanLinc.Speed enumeration so this
            # will work.  It handles on/off for the fan_on_off topic as well
            # as speeds for the fan_speed topic.
            cmd = data.get('cmd', None)
            fan_speed = getattr(Dev.FanLinc.Speed, cmd.upper(), None)
            if fan_speed is None:
                raise ValueError("Can't map cmd '%s' to fan mode" % cmd)

            reason = data.get("reason", "")
            self.device.fan_set(fan_speed, reason=reason)
        except:
            LOG.exception("Invalid fan set speed command: %s", data)

    #-----------------------------------------------------------------------
