#===========================================================================
#
# MQTT Base Topic
#
#===========================================================================
from ... import log

LOG = log.get_logger()


class BaseTopic:
    """Abstract Class for MQTT Topics
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device):  The Insteon object to link to.
        """
        self.mqtt = mqtt
        self.device = device
        self.class_name = None  # This should be amended by each class
        # Any topics added here are available in discovery templates using the
        # key as the variable name.  The key should be the yaml key for the
        # topic
        self.topics = {}

    #-----------------------------------------------------------------------
    def base_template_data(self, **kwargs):
        """Create the Jinja templating data variables for use in topics.

        As the base template, this provides the immutable values such as
        address and name.

        Args:
          button (int):  The button (group) ID (1-8) of the Insteon button
                 that was triggered.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        data = {"address" : self.device.addr.hex,
                "name" : self.device.addr.hex}
        if self.device.name:
            data['name'] = self.device.name
        if 'button' in kwargs and kwargs['button'] is not None:
            data['button'] = kwargs['button']
        return data
