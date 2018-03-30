#===========================================================================
#
# MQTT leak sensor device
#
#===========================================================================
import time
from .. import log
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class Leak:
    """Leak battery powered sensor.

    Leak sensors don't support any input commands - they're sleeping until
    activated so they can't respond to commands.  Leak sensors have a
    state topic and a heartbeat topic they will publish to.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt:     The MQTT main interface.
          device:   The Insteon LeakSensor object to link to.
        """
        self.mqtt = mqtt
        self.device = device

        # Default values for the topics.
        self.msg_wet = MsgTemplate(
            topic='insteon/{{address}}/wet',
            payload='{{is_wet_str.upper()}}',
            )
        self.msg_heartbeat = MsgTemplate(
            topic='insteon/{{address}}/heartbeat',
            payload='{{heartbeat_str}}',
            )

        # Connect the two signals from the insteon device so we get notified
        # of changes.
        device.signal_active.connect(self.handle_active)
        device.signal_heartbeat.connect(self.handle_heartbeat)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['leak'].
          qos:      The default quality of service level to use.
        """
        data = config.get("leak", None)
        if not data:
            return

        self.msg_wet.load_config(data, 'wet_dry_topic', 'wet_dry_payload', qos)
        self.msg_heartbeat.load_config(data, 'heartbeat_topic',
                                       'heartbeat_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Args:
          link:   The MQTT network client to use.
          qos:    The quality of service to use.
        """
        pass

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link:   The MQTT network client to use.
        """
        pass

    #-----------------------------------------------------------------------
    def handle_active(self, device, is_wet):
        """Device wet/dry on/off callback.

        This is triggered via signal when the Insteon device detects
        wet or dry. It will publish an MQTT message with the new
        state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_wet:   (bool) True for wet, False for dry.
        """
        LOG.info("MQTT received wet/dry change %s wet= %s", device.label,
                 is_wet)

        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            "is_wet" : 1 if is_wet else 0,
            "is_wet_str" : "on" if is_wet else "off",
            "is_dry" : 0 if is_wet else 1,
            "is_dry_str" : "off" if is_wet else "on",
            "state" : "wet" if is_wet else "dry",
            }

        self.msg_wet.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_heartbeat(self, device, is_heartbeat):
        """Device heartbeat on/off callback.

        This is triggered via signal when the Insteon device receive a
        heartbeat. It will publish an MQTT message with the new date.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_heartbeat:   (bool) True for heartbeat, False for not.
        """
        LOG.info("MQTT received heartbeat %s = %s", device.label,
                 is_heartbeat)

        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            "is_heartbeat" : 1 if is_heartbeat else 0,
            "heartbeat_str" : time.time() if is_heartbeat else "",
            }

        self.msg_heartbeat.publish(self.mqtt, data)
