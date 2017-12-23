#===========================================================================
#
# MQTT smoke bridge sensor device
#
#===========================================================================
from .. import log
from .. import device as IDev
from .Base import Base
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class SmokeBridge(Base):
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        super().__init__()

        self.mqtt = mqtt
        self.device = device

        self.msg_smoke = MsgTemplate(
            topic='insteon/{{address}}/smoke',
            payload='{{on_str.upper()}}',
            )
        self.msg_co = MsgTemplate(
            topic='insteon/{{address}}/co',
            payload='{{on_str.upper()}}',
            )
        self.msg_battery = MsgTemplate(
            topic='insteon/{{address}}/battery',
            payload='{{on_str.upper()}}',
            )
        self.msg_error = MsgTemplate(
            topic='insteon/{{address}}/error',
            payload='{{on_str.upper()}}',
            )

        device.signal_state_change.connect(self.handle_change)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """TODO: doc
        """
        data = config.get("smoke_bridge", None)
        if not data:
            return

        self.msg_smoke.load_config(data, 'smoke_topic', 'smoke_payload', qos)
        self.msg_co.load_config(data, 'co_topic', 'co_payload', qos)
        self.msg_battery.load_config(data, 'battery_topic', 'battery_payload',
                                     qos)
        self.msg_error.load_config(data, 'error_topic', 'error_payload', qos)

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
        LOG.info("MQTT received active change %s = %s", device.label,
                 condition)

        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "on" : 1,
            "on_str" : "on",
            }

        Type = IDev.SmokeBridge.Type

        # Clear condition resets the status to off and calls all the
        # conditions.
        clear = condition == Type.CLEAR
        if clear:
            data["on"] = 0
            data["on_str"] = "off"

        if clear or condition == Type.SMOKE:
            self.msg_smoke.publish(self.mqtt, data)

        if clear or condition == Type.CO:
            self.msg_co.publish(self.mqtt, data)

        if clear or condition == Type.LOW_BATTERY:
            self.msg_battery.publish(self.mqtt, data)

        if clear or condition == Type.ERROR:
            self.msg_error.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
