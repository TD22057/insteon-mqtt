#===========================================================================
#
# MQTT Base Topic
#
#===========================================================================
import time
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

        # This defines the default class name that is used when searching for
        # discovery templates.
        self.default_discovery_cls = None

        # Any topics added here are available in discovery templates using the
        # key as the variable name.  The key should be the yaml key for the
        # topic
        self.rendered_topic_map = {}

        # This should be a list of group numbers for which state, set, and
        # scene topics will be generated such as state_topic_1, if empty
        # only the default state topics and command topics will be generated
        self.extra_topic_nums = []

    #-----------------------------------------------------------------------
    def base_template_data(self, **kwargs):
        """Create the Jinja templating data variables for use in topics.

        As the base template, this provides the immutable values such as
        address, name, and timestamp.

        Args:
          button (int):  The button (group) ID (1-8) of the Insteon button
                 that was triggered.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        data = {"address" : self.device.addr.hex,
                "name" : self.device.addr.hex,
                "timestamp": int(time.time())}
        if self.device.name:
            data['name'] = self.device.name
        if 'button' in kwargs and kwargs['button'] is not None:
            data['button'] = kwargs['button']
        return data
