#===========================================================================
#
# MQTT On/Off device interface
#
#===========================================================================
import json
import jinja2
from .. import log

LOG = log.get_logger()


class OnOff:
    """TODO: doc
    """
    def __init__(self, mqtt):
        """TODO: doc
        """
        self.mqtt = mqtt

        self.set_payload = jinja2.Template("{{value}}")
        self.state_topic = jinja2.Template("insteon/state/{{address}}")
        self.state_payload = jinja2.Template("{{on_txt}}")

    #-----------------------------------------------------------------------
    def load_config(self, config):
        data = config.get("on_off", None)
        if not data:
            return

        for key in ["set_payload", "state_topic", "state_payload"]:
            value = data.get(key, None)
            if value.strip():
                templ = jinja2.Template(value)
                setattr(self, key, templ)

    #-----------------------------------------------------------------------
    def connect(self, device):
        """TODO: doc
        """
        device.signal_active.connect(self.active_cb)

    #-----------------------------------------------------------------------
    # TODO: handle_cmd in Base
    def handle_set(self, device, payload):
        """TODO: doc
        """
        value = payload.decode("utf-8").strip()
        try:
            value_json = json.loads(value)
        except:
            value_json = {}

        try:
            result = self.set_payload.render(value=value, json=value_json)
        except:
            LOG.exception("On/Off %s can't parse set payload '%s'",
                          device.addr, value)
            return

        lower = value.lower()
        if lower == "on":
            is_active = True
        elif if lower == "off":
            is_active = False
        else:
            try:
                is_active = float(value) > 0
            except:
                LOG.exception("On/Off %s invalid set result '%s'",
                              device.addr, value)
                return

        try:
            is_instant = bool(value_json.get("instant", False))
        except:
            LOG.exception("On/Off %s invalid 'instant' json key '%s'",
                          device.addr, value_json.get("instant"))
            is_instant = False

        device.set(is_active, is_instant)

    #-----------------------------------------------------------------------
    def active_cb(self, device, is_active):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_active (bool) True for on, False for off.
        """
        LOG.info("On/Off MQTT device %s active=%s", device.addr, is_active)

        topic_data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            }
        payload_data = {
            "on" : 1 if is_active else 0,
            "on_txt" : "ON" if is_active else "OFF",
            "level_255" : 255 if is_active else 0,
            "level_100" : 100 if is_active else 0,
            }

        try:
            topic = self.state_topic.render(topic_data)
            payload = self.state_topic.render(payload_data)
        except:
            LOG.exception("Error creating MQTT packet for On/Off Device %s",
                          device.addr)
            return

        self.mqtt.publish(topic, payload)

    #-----------------------------------------------------------------------
