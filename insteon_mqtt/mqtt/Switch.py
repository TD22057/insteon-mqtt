#===========================================================================
#
# MQTT On/Off switch device
#
#===========================================================================
from .. import log
from .Base import Base
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class Switch(Base):
    """TODO: doc
    """
    def __init__(self, mqtt, device, handle_active=True):
        """TODO: doc
        """
        super().__init__()

        self.mqtt = mqtt
        self.device = device

        # Output state change reporting template.
        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state',
            payload='{{on_str.lower()}}',
            )

        # Input on/off command template.
        self.msg_on_off = MsgTemplate(
            topic='insteon/{{address}}/set',
            payload='{ "cmd" : "{{value.lower()}}" }',
            )

        if handle_active:
            device.signal_active.connect(self.handle_active)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """TODO: doc
        """
        self.load_switch_config(config.get("switch", None), qos)

    #-----------------------------------------------------------------------
    def load_switch_config(self, config, qos):
        """TODO: doc
        """
        if not config:
            return

        self.msg_state.load_config(config, 'state_topic', 'state_payload', qos)
        self.msg_on_off.load_config(config, 'on_off_topic', 'on_off_payload',
                                    qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """TODO: doc
        """
        topic = self.msg_on_off.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_set)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """TODO: doc
        """
        topic = self.msg_on_off.render_topic(self.template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def template_data(self, is_active=None):
        """TODO: doc
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            }

        if is_active is not None:
            data["on"] = 1 if is_active else 0,
            data["on_str"] = "on" if is_active else "off"

        return data

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

        data = self.template_data(is_active)
        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_set(self, client, data, message):
        """TODO: doc
        """
        LOG.info("Switch message %s %s", message.topic, message.payload)

        data = self.msg_on_off.to_json(message.payload)
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
