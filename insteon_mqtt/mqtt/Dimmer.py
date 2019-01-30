#===========================================================================
#
# MQTT dimmer switch device
#
#===========================================================================
from .. import log
from .MsgTemplate import MsgTemplate
from .Switch import Switch

LOG = log.get_logger()


class Dimmer(Switch):
    """Insteon dimmer MQTT interface.

    Dimmers will report their state and brightness (level) and can be
    commanded to turn on and off or on at a specific level (0-255).
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt:     The MQTT main interface.
          device:   The Insteon Dimmer object to link to.
        """
        super().__init__(mqtt, device, handle_active=False)

        # Output state change reporting template.
        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state',
            payload='{ "state" : "{{on_str.upper()}}", '
                    '"brightness" : {{level_255}} }',
            )
            
        # Output faston state change reporting template.
        self.msg_faston_state = MsgTemplate(
            topic='insteon/{{address}}/fastonstate',
            payload='{{on_str.lower()}}',
            )
            
        # Output manual increment state change reporting template.
        self.msg_manual_state = MsgTemplate(
            topic='insteon/{{address}}/manualstate',
            payload='{{manual}}',
            )

        # Input level command template.
        self.msg_level = MsgTemplate(
            topic='insteon/{{address}}/level',
            payload='{ "cmd" : "{{json.state.lower()}}", '
                    '"level" : {{json.brightness}} }',
            )

        # Input scene on/off command template.
        self.msg_scene_on_off = MsgTemplate(
            topic='insteon/{{address}}/scene',
            payload='{ "cmd" : "{{value.lower()}}" }',
            )

        device.signal_level_changed.connect(self.handle_level_changed)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['dimmer'].
          qos:      The default quality of service level to use.
        """
        data = config.get("dimmer", None)
        super().load_switch_config(data, qos)
        self.load_dimmer_config(data, qos)

    #-----------------------------------------------------------------------
    def load_dimmer_config(self, config, qos):
        """TODO: doc
        """
        if not config:
            return

        # The Switch base class will load the msg_state, msg_faston_state and msg_manual_state template for us.
        self.msg_level.load_config(config, 'level_topic', 'level_payload', qos)
        self.msg_scene_on_off.load_config(config, 'scene_on_off_topic',
                                          'scene_on_off_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Args:
          link:   The MQTT network client to use.
          qos:    The quality of service to use.
        """
        super().subscribe(link, qos)

        topic = self.msg_level.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_set_level)

        topic = self.msg_scene_on_off.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_scene)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link:   The MQTT network client to use.
        """
        super().unsubscribe(link)

        topic = self.msg_level.render_topic(self.template_data())
        self.mqtt.unsubscribe(topic)

        topic = self.msg_scene_on_off.render_topic(self.template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    # pylint: disable=arguments-differ
    def template_data(self, level=None, faston=False, manual_increment=None):
        """TODO: doc
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            }

        if level is not None:
            data["on"] = 1 if level else 0
            data["on_str"] = "on" if level else "off"
            data["level_255"] = level
            data["level_100"] = int(100.0 * level / 255.0)
            data['fast_on'] = 1 if faston else 0
        if manual_increment is not None:
            data['manual'] = manual_increment

        return data

    #-----------------------------------------------------------------------
    def handle_level_changed(self, device, level, faston=False, manual_increment=None):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          level     (int) True for on, False for off.
          faston:  (bool) True if device toggled faston/off
          manual_increment: (int) 0=down, 2=up, 1=stop
        """
        LOG.info("MQTT received level change %s = %s %s, manual: %s", device.label, level,
                'FASTON' if (faston and level>0) else 'FASTOFF' if (faston and level == 0) else '',
                manual_increment)

        data = self.template_data(level, faston, manual_increment)
        if manual_increment is not None:
            self.msg_manual_state.publish(self.mqtt, data)
        else:
            if faston:
                self.msg_faston_state.publish(self.mqtt, data)
            self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_set_level(self, client, data, message):
        """TODO: doc
        """
        LOG.info("Dimmer message %s %s", message.topic, message.payload)

        data = self.msg_level.to_json(message.payload)
        if not data:
            return

        LOG.info("Dimmer input command: %s", data)
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
    def handle_scene(self, client, data, message):
        """TODO: doc
        """
        LOG.debug("Dimmer message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_scene_on_off.to_json(message.payload)
        LOG.info("Dimmer input command: %s", data)

        try:
            cmd = data.get('cmd')
            if cmd == 'on':
                is_on = True
            elif cmd == 'off':
                is_on = False
            else:
                raise Exception("Invalid dimmer cmd input '%s'" % cmd)

            group = int(data.get('group', 0x01))
        except:
            LOG.exception("Invalid dimmer command: %s", data)
            return

        # Tell the device to trigger the scene command.
        self.device.scene(is_on, group)

    #-----------------------------------------------------------------------
