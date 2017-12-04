#===========================================================================
#
# MQTT dimmer switch device
#
#===========================================================================
import json
import jinja2
from .. import log
from .Switch import Switch
from . import util

LOG = log.get_logger()


class Dimmer(Switch):
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        super().__init__(mqtt, device, handle_active=False)

        self.load_topic_template('state_topic', 'insteon/{{address}}/state')
        self.load_payload_template('state_payload',
                                   '{ "state" : "{{on_str.upper()}}", '
                                   '"brightness" : {{level_255}} }')

        self.load_topic_template('level_topic', 'insteon/{{address}}/level')
        self.load_payload_template('level_payload',
                                   '{ "cmd" : "{{json.state.lower()}}", '
                                   '"level" : {{json.brightness}} }')

        device.signal_level_changed.connect(self.handle_level_changed)

    #-----------------------------------------------------------------------
    def load_config(self, config):
        """TODO: doc
        """
        data = config.get("dimmer", None)
        super().load_switch_config(data)
        self.load_dimmer_config(data)

    #-----------------------------------------------------------------------
    def load_dimmer_config(self, config):
        """TODO: doc
        """
        if not config:
            return

        self.load_topic_template('level_topic',
                                 config.get('level_topic', None))
        self.load_payload_template('level_payload',
                                   config.get('level_payload', None))

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """TODO: doc
        """
        super().subscribe(link, qos)
        link.subscribe(self.level_topic, qos, self.handle_set)

    #-----------------------------------------------------------------------
    def unsubscribe(self):
        """TODO: doc
        """
        super().unsubscribe(link, qos)
        link.unsubscribe(self.level_topic, qos)

    #-----------------------------------------------------------------------
    def handle_level_changed(self, device, level):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          level     (int) True for on, False for off.
        """
        LOG.info("MQTT received level change %s '%s' = %s",
                 device.addr, device.name, level)

        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "on" : 1 if level else 0,
            "on_str" : "on" if level else "off",
            "level_255" : level,
            "level_100" : int( 100.0 * level / 255.0),
            }

        payload = self.render( 'state_payload', data)
        if not payload:
            return

        self.mqtt.publish(self.state_topic, payload)

    #-----------------------------------------------------------------------
    def handle_set(self, client, data, message):
        """TODO: doc
        """
        LOG.info("Dimmer message %s %s", message.topic, message.payload)

        data = self.input_to_json(message.payload, 'level_payload')
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

        self.device.set(level, instant)

    #-----------------------------------------------------------------------
