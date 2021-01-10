#===========================================================================
#
# MQTT On/Off switch device
#
#===========================================================================
from .. import log
from .. import on_off
from .MsgTemplate import MsgTemplate
from . import util
from .SceneTopic import SceneTopic
from .StateTopic import StateTopic
from .ManualTopic import ManualTopic

LOG = log.get_logger()


class Switch(StateTopic, SceneTopic, ManualTopic):
    """MQTT interface to an Insteon on/off switch.

    This class connects to a device.Switch object and converts it's
    output state changes to MQTT messages.  It also subscribes to topics to
    allow input MQTT messages to change the state of the Insteon device.

    Switches will report their state and can be commanded to turn on and off.
    """

    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Switch):  The Insteon object to link to.
        """
        # Setup the Topics
        super().__init__(mqtt, device)

        # Input on/off command template.
        self.msg_on_off = MsgTemplate(
            topic='insteon/{{address}}/set',
            payload='{ "cmd" : "{{value.lower()}}" }')

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['switch'].
          qos (int):  The default quality of service level to use.
        """
        data = config.get("switch", None)
        if not data:
            return

        # Load the various topics
        self.load_scene_data(data, qos)
        self.load_state_data(data, qos)
        self.load_manual_data(data, qos)

        self.msg_on_off.load_config(data, 'on_off_topic', 'on_off_payload',
                                    qos)

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
        topic = self.msg_on_off.render_topic(self.base_template_data())
        link.subscribe(topic, qos, self._input_on_off)

        self.scene_subscribe(link, qos)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        topic = self.msg_on_off.render_topic(self.base_template_data())
        link.unsubscribe(topic)

        self.scene_unsubscribe(link)

    #-----------------------------------------------------------------------
    def template_data(self, **kwargs):
        """Create the Jinja templating data variables for on/off messages.

        Args:
          is_on (bool):  The on/off state of the switch.  If None, on/off and
                mode attributes are not added to the data.
          mode (on_off.Mode):  The on/off mode state.
          manual (on_off.Manual):  The manual mode state.  If None, manual
                 attributes are not added to the data.
          reason (str):  The reason the device was triggered.  This is an
                 arbitrary string set into the template variables.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        # Set up the variables that can be used in the templates.
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            }

        if 'is_on' in kwargs and kwargs['is_on'] is not None:
            data["on"] = 1 if kwargs['is_on'] else 0
            data["on_str"] = "on" if kwargs['is_on'] else "off"
            data["mode"] = str(on_off.Mode.NORMAL)
            data["fast"] = 0
            data["instant"] = 0
            if 'mode' in kwargs:
                data["mode"] = str(kwargs['mode'])
                data["fast"] = 1 if kwargs['mode'] == on_off.Mode.FAST else 0
                data["instant"] = 0
                if kwargs['mode'] == on_off.Mode.INSTANT:
                    data["instant"] = 1
            data["reason"] = ""
            if 'reason' in kwargs and kwargs['reason'] is not None:
                data["reason"] = kwargs['reason']

        if 'manual' in kwargs and kwargs['manual'] is not None:
            data["manual_str"] = str(kwargs['manual'])
            data["manual"] = kwargs['manual'].int_value()
            data["manual_openhab"] = kwargs['manual'].openhab_value()
            data["reason"] = ""
            if 'reason' in kwargs and kwargs['reason'] is not None:
                data["reason"] = kwargs['reason']

        return data

    #-----------------------------------------------------------------------
    def _input_on_off(self, client, data, message):
        """Handle an input on/off change MQTT message.

        This is called when we receive a message on the on/off MQTT topic
        subscription.  Parse the message and pass the command to the Insteon
        device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.debug("Switch message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_on_off.to_json(message.payload)
        LOG.info("Switch input command: %s", data)
        try:
            # Tell the device to update it's state.
            is_on, mode, transition = util.parse_on_off(data)
            if mode == on_off.Mode.RAMP or transition is not None:
                LOG.error("Light ON/OFF at Ramp Rate not supported with "
                          "switches - ignoring ramp rate.")
            if mode == on_off.Mode.RAMP:  # Not supported
                mode = on_off.Mode.NORMAL
            reason = data.get("reason", "")
            self.device.set(level=is_on, mode=mode, reason=reason)
        except:
            LOG.error("Invalid switch on/off command: %s", data)

    #-----------------------------------------------------------------------
