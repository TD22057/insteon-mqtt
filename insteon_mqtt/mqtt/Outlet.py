#===========================================================================
#
# MQTT On/Off outlet device
#
#===========================================================================
import functools
from .. import log
from .. import on_off
from .MsgTemplate import MsgTemplate
from . import util

LOG = log.get_logger()


class Outlet:
    """MQTT interface to an Insteon on/off outlet.

    This class connects to a device.Outlet object and converts it's
    output state changes to MQTT messages.  It also subscribes to topics to
    allow input MQTT messages to change the state of the Insteon device.

    Outlets will report their state (1/socket) and can be commanded to turn
    on and off.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Outlet):  The Insteon object to link to.
        """
        self.mqtt = mqtt
        self.device = device

        # Output state change reporting template.
        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state/{{button}}',
            payload='{{on_str.lower()}}')

        # Input on/off command template.
        self.msg_on_off = MsgTemplate(
            topic='insteon/{{address}}/set/{{button}}',
            payload='{ "cmd" : "{{value.lower()}}" }')

        # Input scene on/off command template.
        self.msg_scene = MsgTemplate(
            topic='insteon/{{address}}/scene/{{button}}',
            payload='{ "cmd" : "{{value.lower()}}" }')

        device.signal_on_off.connect(self._insteon_on_off)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['outlet'].
          qos (int):  The default quality of service level to use.
        """
        data = config.get("outlet", None)
        if not data:
            return

        self.msg_state.load_config(data, 'state_topic', 'state_payload', qos)
        self.msg_on_off.load_config(data, 'on_off_topic', 'on_off_payload',
                                    qos)
        self.msg_scene.load_config(data, 'scene_topic', 'scene_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        # Connect input topics for groups 1 and 2 (top and bottom sockets).
        # Create a function that will call the input callback with the right
        # group number set for each socket.
        for group in [1, 2]:
            handler = functools.partial(self._input_on_off, group=group)
            data = self.template_data(button=group)

            topic = self.msg_on_off.render_topic(data)
            link.subscribe(topic, qos, handler)

            handler = functools.partial(self._input_scene, group=group)
            topic = self.msg_scene.render_topic(data)
            link.subscribe(topic, qos, handler)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        for group in [1, 2]:
            data = self.template_data(button=group)

            topic = self.msg_on_off.render_topic(data)
            link.unsubscribe(topic)

            topic = self.msg_scene.render_topic(data)
            link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def template_data(self, is_on=None, button=None, mode=on_off.Mode.NORMAL,
                      reason=None):
        """Create the Jinja templating data variables for on/off messages.

        Args:
          button (int):  The button (group) ID (1-2) of the Insteon button
                 that was triggered.
          is_on (bool):  True for on, False for off.  If None, on/off and
                mode attributes are not added to the data.
          mode (on_off.Mode):  The on/off mode state.
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

        if button is not None:
            data["button"] = button

        if is_on is not None:
            data["on"] = 1 if is_on else 0
            data["on_str"] = "on" if is_on else "off"
            data["mode"] = str(mode)
            data["fast"] = 1 if mode == on_off.Mode.FAST else 0
            data["instant"] = 1 if mode == on_off.Mode.INSTANT else 0
            data["reason"] = reason if reason is not None else ""

        return data

    #-----------------------------------------------------------------------
    def _insteon_on_off(self, device, group, is_on, mode=on_off.Mode.NORMAL,
                        reason=""):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device turns on or off.
        It will publish an MQTT message with the new state.

        Args:
          device (device.Outlet):  The Insteon device that changed.
          group (int):  The socket number (1 or 2) that was changed.
          is_on (bool):  True for on, False for off.  If None, on/off and
                mode attributes are not added to the data.
          mode (on_off.Mode):  The on/off mode state.
          reason (str):  The reason the device was triggered.  This is an
                 arbitrary string set into the template variables.
        """
        LOG.info("MQTT received on/off %s grp: %s on: %s %s '%s'",
                 device.label, group, is_on, mode, reason)

        data = self.template_data(is_on, group, mode, reason=reason)
        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _input_on_off(self, client, data, message, group):
        """Handle an input on/off change MQTT message.

        This is called when we receive a message on the on/off MQTT topic
        subscription.  Parse the message and pass the command to the Insteon
        device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.debug("Outlet btn %s message %s %s", group, message.topic,
                  message.payload)

        # Parse the input MQTT message.
        data = self.msg_on_off.to_json(message.payload)
        LOG.info("Outlet input command: %s", data)

        try:
            # Tell the device to update it's state.
            is_on, mode = util.parse_on_off(data)
            reason = data.get("reason", "")
            self.device.set(level=is_on, group=group, mode=mode, reason=reason)
        except:
            LOG.exception("Invalid Outlet on/off command: %s", data)

    #-----------------------------------------------------------------------
    def _input_scene(self, client, data, message, group):
        """Handle an input scene MQTT message.

        This is called when we receive a message on the scene trigger MQTT
        topic subscription.  Parse the message and pass the command to the
        Insteon device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.debug("Outlet btn %s message %s %s", group, message.topic,
                  message.payload)

        # Parse the input MQTT message.
        data = self.msg_scene.to_json(message.payload)
        LOG.info("Outlet input command: %s", data)

        try:
            # Scenes don't support modes so don't parse that element.
            is_on = util.parse_on_off(data, have_mode=False)
            reason = data.get("reason", "")
            self.device.scene(is_on, group, reason)
        except:
            LOG.exception("Invalid Outlet scene command: %s", data)

    #-----------------------------------------------------------------------
