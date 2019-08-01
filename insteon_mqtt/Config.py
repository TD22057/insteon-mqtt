#===========================================================================
#
# Configuration file utiltiies.
#
#===========================================================================

__doc__ = """Configuration file utilties
"""

#===========================================================================
from ruamel.yaml import YAML
from . import device


class Config:
    """Config file class

    This class handles the loading, parsing, and saving of the configuration
    file.
    """
    def __init__(self, path):
        self.path = path
        # Configuration file input description to class map.
        self.devices = {
            # Key is config file input.  Value is tuple of (class, **kwargs)
            # of the class to use and any extra keyword args to pass to the
            # constructor.
            'dimmer' : (device.Dimmer, {}),
            'battery_sensor' : (device.BatterySensor, {}),
            'fan_linc' : (device.FanLinc, {}),
            'io_linc' : (device.IOLinc, {}),
            'keypad_linc' : (device.KeypadLinc, {'dimmer' : True}),
            'keypad_linc_sw' : (device.KeypadLinc, {'dimmer' : False}),
            'leak' : (device.Leak, {}),
            'mini_remote4' : (device.Remote, {'num_button' : 4}),
            'mini_remote8' : (device.Remote, {'num_button' : 8}),
            'motion' : (device.Motion, {}),
            'outlet' : (device.Outlet, {}),
            'smoke_bridge' : (device.SmokeBridge, {}),
            'switch' : (device.Switch, {}),
            'thermostat' : (device.Thermostat, {}),
            }
        self.data = []

        # Initialize the config data
        self.load()

#===========================================================================
    def load(self):
        """Load or reloads the configuration file.  Called on object init
        """
        with open(self.path, "r") as f:
            yaml = YAML()
            yaml.preserve_quotes = True
            self.data = yaml.load(f)

#===========================================================================
    def apply(self, mqtt, modem):
        """Apply the configuration to the main MQTT and modem objects.

        Args:
          mqtt (mqtt.Mqtt):  The main MQTT handler.
          modem (Modem):  The PLM modem object.
        """
        # We must load the MQTT config first - loading the insteon config
        # triggers device creation and we need the various MQTT config's set
        # before that.
        mqtt.load_config(self)
        modem.load_config(self)

#===========================================================================
    def find(self, name):
        """Find a device class from a description.

        Valid inputs are defined in the self.devices dictionary.

        Raises:
          Exception if the input device is unknown.

        Args:
          name (str):  The device type name.

        Returns:
          Returns a tuple of the device class to use for the input and
          any extra keyword args to pass to the device class constructor.
        """
        dev = self.devices.get(name.lower(), None)
        if not dev:
            raise Exception("Unknown device name '%s'.  Valid names are "
                            "%s." % (name, self.devices.keys()))

        return dev
