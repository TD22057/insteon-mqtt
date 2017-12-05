#===========================================================================
#
# MQTT smoke bridge sensor device
#
#===========================================================================
from .. import log
from .. import devices
from .Base import Base

LOG = log.get_logger()


class SmokeBridge(Base):
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        super().__init__(mqtt, device)

        self.load_topic_template('smoke_topic', 'insteon/{{address}}/smoke')
        self.load_payload_template('smoke_payload', '{{on_str.upper()}}')

        self.load_topic_template('co_topic', 'insteon/{{address}}/co')
        self.load_payload_template('co_payload', '{{on_str.upper()}}')

        self.load_topic_template('battery_topic',
                                 'insteon/{{address}}/battery')
        self.load_payload_template('battery_payload', '{{on_str.upper()}}')

        self.load_topic_template('error_topic', 'insteon/{{address}}/error')
        self.load_payload_template('error_payload', '{{on_str.upper()}}')

        device.signal_state_change.connect(self.handle_change)

    #-----------------------------------------------------------------------
    def load_config(self, config):
        """TODO: doc
        """
        data = config.get("motion", None)
        if not data:
            return

        self.load_topic_template('smoke_topic', data.get('smoke_topic', None))
        self.load_payload_template('smoke_payload',
                                   data.get('smoke_payload', None))

        self.load_topic_template('co_topic', data.get('co_topic', None))
        self.load_payload_template('co_payload', data.get('co_payload', None))

        self.load_topic_template('battery_topic',
                                 data.get('battery_topic', None))
        self.load_payload_template('battery_payload',
                                   data.get('battery_payload', None))

        self.load_topic_template('error_topic', data.get('error_topic', None))
        self.load_payload_template('error_payload',
                                   data.get('error_payload', None))

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """TODO: doc
        """
        pass

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """TODO: doc
        """
        pass

    #-----------------------------------------------------------------------
    def handle_change(self, device, condition):
        """Device active condition callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:    (device.Base) The Insteon device that changed.
          condition: SmokeBridge.Type condition code.
        """
        LOG.info("MQTT received active change %s '%s' = %s",
                 device.addr, device.name, condition)

        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "on" : 1,
            "on_str" : "on",
            }

        Type = devices.SmokeBridge.Type

        # Clear condition resets the status to off and calls all the
        # conditions.
        clear = condition == Type.CLEAR
        if clear:
            data["on"] = 0
            data["on_str"] = "off"

        if clear or condition == Type.SMOKE:
            payload = self.render('smoke_payload', data)
            self.mqtt.publish(self.smoke_topic, payload)

        if clear or condition == Type.CO:
            payload = self.render('co_payload', data)
            self.mqtt.publish(self.co_topic, payload)

        if clear or condition == Type.LOW_BATTERY:
            payload = self.render('battery_payload', data)
            self.mqtt.publish(self.battery_topic, payload)

        if clear or condition == Type.ERROR:
            payload = self.render('error_payload', data)
            self.mqtt.publish(self.error_topic, payload)

    #-----------------------------------------------------------------------
