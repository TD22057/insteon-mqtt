#===========================================================================
#
# MQTT keypad linc which is a dimmer plus 4 or 8 button remote.
#
#===========================================================================
import functools
from .. import log
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class KeypadLinc:
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        self.mqtt = mqtt
        self.device = device

        # Output on/off state change reporting template.
        self.msg_btn_state = MsgTemplate(
            topic='insteon/{{address}}/state/{{button}}',
            payload='{{on_str.lower()}}',
            )
            
        # Output faston state change reporting template.
        self.msg_faston_state = MsgTemplate(
            topic='insteon/{{address}}/fastonstate/{{button}}',
            payload='{{on_str.lower()}}',
            )
            
        self.msg_btn_manual_state = MsgTemplate(
            topic='insteon/{{address}}/manualstate/{{button}}',
            payload='{{manual}}',
            )

        # Input on/off command template.
        self.msg_btn_on_off = MsgTemplate(
            topic='insteon/{{address}}/set/{{button}}',
            payload='{ "cmd" : "{{value.lower()}}" }',
            )

        # Input scene on/off command template.
        self.msg_btn_scene = MsgTemplate(
            topic='insteon/{{address}}/scene/{{button}}',
            payload='{ "cmd" : "{{value.lower()}}" }',
            )

        self.msg_dimmer_state = None
        self.msg_dimmer_level = None
        self.msg_faston_dimmer_state = None
        if self.device.is_dimmer:
            # Output dimmer state change reporting template.
            self.msg_dimmer_state = MsgTemplate(
                topic='insteon/{{address}}/state/1',
                payload='{ "state" : "{{on_str.upper()}}", '
                        '"brightness" : {{level_255}} }',
                )
                
            self.msg_faston_dimmer_state = MsgTemplate(
                topic='insteon/{{address}}/fastonstate/1',
                payload='{ "state" : "{{on_str.upper()}}", '
                        '"brightness" : {{level_255}} }',
                )

            # Input dimmer level command template.
            self.msg_dimmer_level = MsgTemplate(
                topic='insteon/{{address}}/level',
                payload='{ "cmd" : "{{json.state.lower()}}", '
                        '"level" : {{json.brightness}} }',
                )

        device.signal_active.connect(self.handle_active)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['keypad_linc'].
          qos:      The default quality of service level to use.
        """
        data = config.get("keypad_linc", None)
        if not data:
            return

        self.msg_btn_state.load_config(data, 'btn_state_topic',
                                       'btn_state_payload', qos)
        self.msg_faston_state.load_config(data, 'faston_state_topic',
                                       'faston_state_payload', qos)
        self.msg_btn_manual_state.load_config(data, 'manual_state_topic',
                                       'manual_state_payload', qos)
        self.msg_btn_on_off.load_config(data, 'btn_on_off_topic',
                                        'btn_on_off_payload', qos)
        self.msg_btn_scene.load_config(data, 'btn_scene_topic',
                                       'btn_scene_payload', qos)

        if self.device.is_dimmer:
            self.msg_dimmer_state.load_config(data, 'dimmer_state_topic',
                                              'dimmer_state_payload', qos)
            self.msg_faston_dimmer_state.load_config(data, 'dimmer_faston_state_topic',
                                              'dimmer_faston_state_payload', qos)
            self.msg_dimmer_level.load_config(data, 'dimmer_level_topic',
                                              'dimmer_level_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Args:
          link:   The MQTT network client to use.
          qos:    The quality of service to use.
        """
        # For dimmers, the button 1 set can be either an on/off or a dimming
        # command.  And the dimmer topic might have the same topic as the
        # on/off command.
        start_group = 1
        if self.device.is_dimmer:
            start_group = 2

            # Create the topic names for button 1.
            data = self.template_data(button=1)
            topic_switch = self.msg_btn_on_off.render_topic(data)
            topic_dimmer = self.msg_dimmer_level.render_topic(data)

            # It's possible for these to be the same.  The btn1 handler will
            # try both payloads to accept either on/off or dimmer commands.
            if topic_switch == topic_dimmer:
                link.subscribe(topic_switch, qos, self.handle_btn1)

            # If they are different, we can pass directly to the right
            # handler for switch commands and dimmer commands.
            else:
                handler = functools.partial(self.handle_set, group=1)
                link.subscribe(topic_switch, qos, handler)

                link.subscribe(topic_dimmer, qos, self.handle_set_level)

        # We need to subscribe to each button topic so we know which one is
        # which.
        for group in range(start_group, 9):
            handler = functools.partial(self.handle_set, group=group)
            data = self.template_data(button=group)

            topic = self.msg_btn_on_off.render_topic(data)
            link.subscribe(topic, qos, handler)

            handler = functools.partial(self.handle_scene, group=group)
            topic = self.msg_btn_scene.render_topic(data)
            link.subscribe(topic, qos, handler)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link:   The MQTT network client to use.
        """
        for group in range(1, 9):
            data = self.template_data(button=group)

            topic = self.msg_btn_on_off.render_topic(data)
            link.unsubscribe(topic)

            topic = self.msg_btn_scene.render_topic(data)
            link.unsubscribe(topic)

        if self.device.is_dimmer:
            data = self.template_data(button=1)
            topic = self.msg_dimmer_level.render_topic(data)
            self.mqtt.unsubscribe(topic)

    #-----------------------------------------------------------------------
    # pylint: disable=arguments-differ
    def template_data(self, level=None, button=None, faston=False, manual_increment=None):
        """TODO: doc
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            "button" : button,
            }

        if level is not None:
            data["on"] = 1 if level else 0
            data["on_str"] = "on" if level else "off"
            data["level_255"] = level
            data["level_100"] = int(100.0 * level / 255.0)
            data['fast_on'] = 1 if faston else 0
        if manual_increment is not None:
            data['manual'] = manual_increment #if level is None

        return data

    #-----------------------------------------------------------------------
    def handle_set(self, client, data, message, group):
        """TODO: doc

        inbound mqtt message for buttons
        """
        LOG.info("KeypadLinc btn %s message %s %s", group, message.topic,
                 message.payload)

        data = self.msg_btn_on_off.to_json(message.payload)
        if not data:
            return

        LOG.info("KeypadLinc btn %s input command: %s", group, data)
        try:
            cmd = data.get('cmd')
            if cmd == 'on':
                self.device.on(group=group)
            elif cmd == 'off':
                self.device.off(group=group)
            else:
                raise Exception("Invalid button cmd input '%s'" % cmd)
        except:
            LOG.exception("Invalid button command: %s", data)
            return

    #-----------------------------------------------------------------------
    def handle_set_level(self, client, data, message):
        """TODO: doc
        """
        LOG.info("KeypadLinc message %s %s", message.topic, message.payload)
        assert self.msg_dimmer_level is not None

        data = self.msg_dimmer_level.to_json(message.payload)
        if not data:
            return

        LOG.info("KeypadLinc input command: %s", data)
        try:
            cmd = data.get('cmd')
            if cmd == 'on':
                level = int(data.get('level'))
            elif cmd == 'off':
                level = 0
            else:
                raise Exception("Invalid dimmer cmd input '%s'" % cmd)

            instant = bool(data.get('instant', False))
        except:
            LOG.exception("Invalid dimmer command: %s", data)
            return

        self.device.set(level=level, instant=instant)

    #-----------------------------------------------------------------------
    def handle_btn1(self, client, data, message):
        """Handle button 1 when the on/off topic == dimmer topic
        """
        LOG.info("KeypadLinc message %s %s", message.topic, message.payload)

        # Try the input as a dimmer command first.
        try:
            if self.msg_dimmer_level.to_json(message.payload, silent=True):
                self.handle_set_level(client, data, message)
                return
        except:
            pass

        # Try the input as an on/off command.
        try:
            if self.msg_btn_on_off.to_json(message.payload, silent=True):
                self.handle_set(client, data, message, 1)
                return
        except:
            pass

        # If we make it here, it's an error.  To log the error, call the
        # regular dimmer handler.
        self.handle_set_level(client, data, message)

    #-----------------------------------------------------------------------
    def handle_scene(self, client, data, message, group):
        """TODO: doc
        """
        LOG.debug("KeypadLinc scene %s message %s %s", group, message.topic,
                  message.payload)

        # Parse the input MQTT message.
        data = self.msg_btn_scene.to_json(message.payload)
        if not data:
            return

        LOG.info("KeypadLinc input command: %s", data)
        try:
            cmd = data.get('cmd')
            if cmd == 'on':
                is_on = True
            elif cmd == 'off':
                is_on = False
            else:
                raise Exception("Invalid KeypadLinc cmd input '%s'" % cmd)
        except:
            LOG.exception("Invalid KeypadLinc command: %s", data)
            return

        # Tell the device to trigger the scene command.
        self.device.scene(is_on, group)

    #-----------------------------------------------------------------------
    def handle_active(self, device, group, level, faston=False, manual_increment=None):
        """Device active button pressed callback.

        This is triggered via signal when the Insteon device button is
        pressed.  It will publish an MQTT message with the button
        number.

        Args:
          device:   (device.Base) The Insteon device that changed.
          group:    (int) The button number 1...n that was pressed.
          level:    (int) The current device level 0...0xff.
          faston:   (bool) True if device was toggled with faston/off
        """
        LOG.info("MQTT received button press %s = btn %s at %s %s, man: %s", device.label,
                 group, level, 'FASTON' if (faston and level>0) else 'FASTOFF' if (faston and level == 0) else '',
                 manual_increment)

        data = self.template_data(level=level, button=group, faston=faston, manual_increment=manual_increment)

        if group == 1 and self.device.is_dimmer:
            if faston:
                self.msg_faston_dimmer_state.publish(self.mqtt, data)
            self.msg_dimmer_state.publish(self.mqtt, data)
        else:
            if manual_increment is not None:
                self.msg_btn_manual_state.publish(self.mqtt, data)
            else:
                if faston:
                    self.msg_faston_state.publish(self.mqtt, data)
                self.msg_btn_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
