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
    activated so they can't respond to commands.  Leak sensors have a state
    topic and a heartbeat topic they will publish to.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Leak):  The Insteon object to link to.
        """
        self.mqtt = mqtt
        self.device = device

        # Default values for the topics.
        self.msg_wet = MsgTemplate(
            topic='insteon/{{address}}/wet',
            payload='{{is_wet_str.lower()}}')
        self.msg_heartbeat = MsgTemplate(
            topic='insteon/{{address}}/heartbeat',
            payload='{{heartbeat_time}}')

        # Connect the two signals from the insteon device so we get notified
        # of changes.
        device.signal_wet.connect(self._insteon_wet)
        device.signal_heartbeat.connect(self._insteon_heartbeat)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['leak'].
          qos (int):  The default quality of service level to use.
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

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        pass

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        pass

    #-----------------------------------------------------------------------
    def template_data(self, is_wet=None, is_heartbeat=None):
        """Create the Jinja templating data variables.

        Args:
          is_wet (bool):  Is the device wet or not.  If this is None, wet/dry
                attributes are not added to the data.
          is_heartbeat (bool):  Is the heartbeat active nor not.  If this is
                       None, heartbeat attributes are not added to the data.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        # Set up the variables that can be used in the templates.
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            }

        if is_wet is not None:
            data["is_wet"] = 1 if is_wet else 0
            data["is_wet_str"] = "on" if is_wet else "off"
            data["is_dry"] = 0 if is_wet else 1
            data["is_dry_str"] = "off" if is_wet else "on"
            data["state"] = "wet" if is_wet else "dry"

        if is_heartbeat is not None:
            data["is_heartbeat"] = 1 if is_heartbeat else 0
            data["is_heartbeat_str"] = "on" if is_heartbeat else "off"
            data["heartbeat_time"] = time.time() if is_heartbeat else 0

        return data

    #-----------------------------------------------------------------------
    def _insteon_wet(self, device, is_wet):
        """Device wet/dry on/off callback.

        This is triggered via signal when the Insteon device detects
        wet or dry. It will publish an MQTT message with the new
        state.

        Args:
          device (device.Leak):  The Insteon device that changed.
          is_wet (bool):  True for wet, False for dry.
        """
        LOG.info("MQTT received wet/dry change %s wet= %s", device.label,
                 is_wet)

        data = self.template_data(is_wet)
        self.msg_wet.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _insteon_heartbeat(self, device, is_heartbeat):
        """Device heartbeat on/off callback.

        This is triggered via signal when the Insteon device receive a
        heartbeat. It will publish an MQTT message with the new date.

        Args:
          device (device.Leak):  The Insteon device that changed.
          is_heartbeat (bool):  True for heartbeat, False for not.
        """
        LOG.info("MQTT received heartbeat %s = %s", device.label,
                 is_heartbeat)

        data = self.template_data(is_heartbeat=is_heartbeat)
        self.msg_heartbeat.publish(self.mqtt, data)
