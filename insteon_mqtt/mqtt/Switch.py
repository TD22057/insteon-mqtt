#===========================================================================
#
# MQTT On/Off switch device
#
#===========================================================================
from .. import log
from .Base import Base

LOG = log.get_logger()


class Switch(Base):
    """TODO: doc
    """
    def __init__(self, mqtt, device, handle_active=True):
        """TODO: doc
        """
        super().__init__(mqtt, device)

        self.load_topic_template('state_topic', 'insteon/{{address}}/state')
        self.load_payload_template('state_payload', '{{on_str.lower()}}')

        # Default payload is ON/OFF or on/off
        self.load_topic_template('on_off_topic', 'insteon/{{address}}/set')
        self.load_payload_template('on_off_payload',
                                   '{ "cmd" : "{{value.lower()}}" }')

        if handle_active:
            device.signal_active.connect(self.handle_active)

    #-----------------------------------------------------------------------
    def load_config(self, config):
        """TODO: doc
        """
        self.load_switch_config(config.get("switch", None))

    #-----------------------------------------------------------------------
    def load_switch_config(self, config):
        """TODO: doc
        """
        if not config:
            return

        self.load_topic_template('state_topic',
                                 config.get('state_topic', None))
        self.load_payload_template('state_payload',
                                   config.get('state_payload', None))

        self.load_topic_template('on_off_topic',
                                 config.get('on_off_topic', None))
        self.load_payload_template('on_off_payload',
                                   config.get('on_off_payload', None))

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """TODO: doc
        """
        link.subscribe(self.on_off_topic, qos, self.handle_set)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """TODO: doc
        """
        link.unsubscribe(self.on_off_topic)

    #-----------------------------------------------------------------------
    def handle_active(self, device, is_active):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_active (bool) True for on, False for off.
        """
        LOG.info("MQTT received active change %s '%s' = %s",
                 device.addr, device.name, is_active)

        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "on" : 1 if is_active else 0,
            "on_str" : "on" if is_active else "off",
            }

        payload = self.render('state_payload', data)
        if not payload:
            return

        self.mqtt.publish(self.state_topic, payload)

    #-----------------------------------------------------------------------
    def handle_set(self, client, data, message):
        """TODO: doc
        """
        LOG.info("Switch message %s %s", message.topic, message.payload)

        data = self.input_to_json(message.payload, 'on_off_payload')
        if not data:
            return

        LOG.info("Switch input command: %s", data)
        try:
            cmd = data.get('cmd')
            if cmd == 'on':
                is_on = True
            elif cmd == 'off':
                is_on = False
            else:
                raise Exception("Invalid Switch cmd input '%s'" % cmd)

            instant = bool(data.get('instant', False))
        except:
            LOG.exception("Invalid switch command: %s", data)
            return

        if is_on:
            self.device.on(instant=instant)
        else:
            self.device.off(instant=instant)

    #-----------------------------------------------------------------------
