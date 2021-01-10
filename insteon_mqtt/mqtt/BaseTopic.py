#===========================================================================
#
# MQTT Base Topic
#
#===========================================================================
from .. import log

LOG = log.get_logger()


class BaseTopic:
    """MQTT interface to an Insteon on/off switch.

    This class connects to a device.Switch object and converts it's
    output state changes to MQTT messages.  It also subscribes to topics to
    allow input MQTT messages to change the state of the Insteon device.

    Switches will report their state and can be commanded to turn on and off.
    """

    def __init__(self, mqtt, device):
        self.mqtt = mqtt
        self.device = device

    #-----------------------------------------------------------------------
    def base_template_data(self, **kwargs):
        """Create the Jinja templating data variables for use in topics.

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
