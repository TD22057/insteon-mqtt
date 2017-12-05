#===========================================================================
#
# MQTT Motion sensor device
#
#===========================================================================
from .. import log
from .Base import Base

LOG = log.get_logger()


class Motion(Base):
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        super().__init__(mqtt, device)

        self.load_topic_template('state_topic', 'insteon/{{address}}/state')
        self.load_payload_template('state_payload', '{{on_str.lower()}}')

        self.load_topic_template('dawn_dusk_topic', 'insteon/{{address}}/dawn')
        self.load_payload_template('dawn_dusk_payload',
                                   '{{is_dawn_str.upper()}}')

        self.load_topic_template('low_battery_topic',
                                 'insteon/{{address}}/low_battery')
        self.load_payload_template('low_battery_payload',
                                   '{{is_low_str.upper()}}')

        device.signal_active.connect(self.handle_active)
        device.signal_dusk.connect(self.handle_dusk)
        device.signal_low_battery.connect(self.handle_low_battery)

    #-----------------------------------------------------------------------
    def load_config(self, config):
        """TODO: doc
        """
        data = config.get("motion", None)
        if not data:
            return

        self.load_topic_template('state_topic',
                                 data.get('state_topic', None))
        self.load_payload_template('state_payload',
                                   data.get('state_payload', None))

        self.load_topic_template('dawn_dusk_topic',
                                 config.get('dawn_dusk_topic', None))
        self.load_payload_template('dawn_dusk_payload',
                                   config.get('dawn_dusk_payload', None))

        self.load_topic_template('low_battery_topic',
                                 config.get('low_battery_topic', None))
        self.load_payload_template('low_battery_payload',
                                   config.get('low_battery_payload', None))

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
    def handle_dusk(self, device, is_dusk):
        """Device dawn/dusk on/off callback.

        This is triggered via signal when the Insteon device detects
        dawn or dusk.  It will publish an MQTT message with the new
        state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_dusk:  (bool) True for dusk, False for dawn.

        """
        LOG.info("MQTT received dusk change %s '%s' = %s",
                 device.addr, device.name, is_dusk)

        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "is_dawn" : 0 if is_dusk else 1,
            "is_dawn_str" : "off" if is_dusk else "on",
            "is_dusk" : 1 if is_dusk else 0,
            "is_dusk_str" : "on" if is_dusk else "off",
            "state" : "dusk" if is_dusk else "dawn",
            }

        payload = self.render('dawn_dusk_payload', data)
        if not payload:
            return

        self.mqtt.publish(self.dawn_dusk_topic, payload)

    #-----------------------------------------------------------------------
    def handle_low_battery(self, device, is_low):
        """Device low battery on/off callback.

        This is triggered via signal when the Insteon device detects a
        low batery It will publish an MQTT message with the new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_low:   (bool) True for low battery, False for not.
        """
        LOG.info("MQTT received low battery %s '%s' = %s",
                 device.addr, device.name, is_low)

        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "is_low" : 1 if is_low else 0,
            "is_low_str" : "on" if is_low else "off",
            }

        payload = self.render('low_battery_payload', data)
        if not payload:
            return

        self.mqtt.publish(self.low_battery_topic, payload)

    #-----------------------------------------------------------------------
